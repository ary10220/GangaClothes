"""Pagos: cobro en caja (CU15) y pago en linea por pasarela (CU17).

Este es el UNICO lugar donde se descuenta inventario por una venta, sin importar
por que metodo se cobro. La regla que impide descontar dos veces:

    UPDATE venta SET estado='pagada' WHERE id=:id AND estado='pendiente'

Solo si esa sentencia toca exactamente una fila se sigue adelante. Dos cobros
simultaneos de la misma venta no pueden pasar ambos: la base deja ganar a uno.
Comprobante, liberacion de la reserva, descuento, movimientos y el pago mismo
van en esa misma transaccion; si una linea no tiene stock, se revierte todo y
la venta sigue pendiente.

Como hablamos con cada proveedor esta en `pasarelas/`:

    caja   efectivo, tarjeta y QR se registran a mano: el cobro ya ocurrio en
           el mostrador y aqui solo se asienta.
    web    la tarjeta va a Stripe (`pasarelas/stripe_gw.py`) y el QR al Banco de
           Credito de Bolivia (`pasarelas/qr_bcp.py`).

El QR es distinto de los demas en una cosa: no se resuelve en la misma llamada.
Se genera, el cliente lo escanea en su banca movil y despues se pregunta al
banco como quedo. Por eso tiene su propia seccion mas abajo.
"""
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.fechas import utc_iso
from app.models.inventario import Inventario, MovimientoInventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Usuario
from app.models.ventas import DetalleVenta, Pago, Reserva, Venta
from app.modules.pagos.pasarelas import cliente_http as http
from app.modules.pagos.pasarelas import qr_bcp, stripe_gw
from app.modules.reservas import service as reservas
from app.modules.ventas import service as ventas

# En caja se cobra en mostrador y el metodo solo se asienta; en linea cada
# metodo pasa por su pasarela.
METODOS_CAJA = {"efectivo", "tarjeta", "qr"}
METODOS_LINEA = {"tarjeta", "qr"}
METODOS = METODOS_CAJA | METODOS_LINEA

# La primera version de la web y la app Flutter mandan "pasarela" para decir
# "tarjeta por Stripe". Se acepta como sinonimo para no romperlas.
ALIAS = {"pasarela": "tarjeta"}

METODOS_POR_CANAL = {"caja": METODOS_CAJA, "web": METODOS_LINEA, "movil": METODOS_LINEA}

# Quien atiende cada metodo, para el comprobante y la bitacora.
PASARELA_DE = {("web", "tarjeta"): "stripe", ("movil", "tarjeta"): "stripe",
               ("web", "qr"): "bcp_qr", ("movil", "qr"): "bcp_qr"}

ETIQUETAS = {"efectivo": "Efectivo", "tarjeta": "Tarjeta", "qr": "QR"}


def normalizar(metodo: str) -> str:
    metodo = (metodo or "").lower().strip()
    return ALIAS.get(metodo, metodo)


def etiqueta(metodo: str | None, pasarela: str | None = None) -> str:
    base = ETIQUETAS.get(metodo or "", metodo or "—")
    if pasarela == "stripe":
        return f"{base} (Stripe)"
    if pasarela == "bcp_qr":
        return f"{base} (BCP)"
    return base


# ------------------------------------------------------------------ utilidades
def _referencia_local() -> str:
    """Referencia propia, para los cobros de mostrador que no tienen pasarela."""
    return f"caja_{uuid4().hex[:20]}"


def _siguiente_comprobante(db: Session) -> str:
    # Con numeros de ancho fijo el maximo alfabetico es tambien el numerico.
    ultimo = db.query(func.max(Venta.nro_comprobante)).scalar()
    numero = int(ultimo.split("-")[1]) + 1 if ultimo else 1
    return f"C-{numero:06d}"


def _salida_pago(pago: Pago) -> dict:
    return {
        "id": pago.id,
        "venta_id": pago.venta_id,
        "metodo": pago.metodo,
        "pasarela": pago.pasarela,
        "etiqueta": etiqueta(pago.metodo, pago.pasarela),
        "monto": float(ventas.dinero(pago.monto)),
        "moneda": pago.moneda,
        "estado": pago.estado,
        "referencia_externa": pago.referencia_externa,
        "fecha": utc_iso(pago.fecha),
    }


def _mensaje_estado(venta: Venta) -> str:
    if venta.estado == "pagada":
        return f"La venta #{venta.id} ya esta pagada (comprobante {venta.nro_comprobante}): no se cobra dos veces"
    if venta.estado == "carrito":
        return f"La venta #{venta.id} sigue en carrito: hay que confirmarla antes de pagar"
    return f"La venta #{venta.id} esta '{venta.estado}': no se puede cobrar"


def _venta_cobrable(db: Session, venta_id: int) -> Venta:
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(404, "Venta no encontrada")
    if venta.estado != "pendiente":
        raise HTTPException(400, _mensaje_estado(venta))
    return venta


def _validar_canal(venta: Venta, metodo: str) -> None:
    if metodo not in METODOS:
        raise HTTPException(400, f"Metodo invalido. Use uno de: {', '.join(sorted(METODOS))}")
    permitidos = METODOS_POR_CANAL.get(venta.canal, set())
    if metodo not in permitidos:
        raise HTTPException(400, f"Una venta por '{venta.canal}' se paga con: {', '.join(sorted(permitidos))}")


def _autorizar(db: Session, venta: Venta, usuario: Usuario, personal: bool, accion: str):
    """En linea paga el dueno de la compra; en caja, el personal con permiso."""
    if venta.canal == "caja":
        if not personal:
            raise HTTPException(403, "Tu rol no tiene el permiso necesario (pagos:crear)")
        return None
    cliente = ventas.cliente_de(db, usuario, accion)
    if venta.cliente_id != cliente.id:
        raise HTTPException(403, "Solo puedes pagar tus propias compras")
    return cliente


# ==============================================================================
#  El cobro en si: lo unico que toca el inventario
# ==============================================================================
def confirmar_cobro(db: Session, venta: Venta, usuario: Usuario, *, metodo: str,
                    pasarela: str | None = None, referencia: str | None = None,
                    monto=None, pago: Pago | None = None) -> dict:
    """Cierra la venta: comprobante, reserva, inventario y el pago, todo junto.

    `pago` permite reusar una fila que ya existia en estado pendiente (es el caso
    del QR, creado al generarlo y confirmado cuando el banco avisa que se pago).
    """
    monto = ventas.dinero(monto if monto is not None else venta.total)

    # 1) Candado contra el doble cobro: solo una operacion pasa de pendiente a pagada.
    cierre = db.execute(
        update(Venta).where(Venta.id == venta.id, Venta.estado == "pendiente")
        .values(estado="pagada").execution_options(synchronize_session=False)
    )
    if cierre.rowcount != 1:
        db.rollback()
        raise HTTPException(400, _mensaje_estado(db.get(Venta, venta.id)))

    # 2) El numero se calcula despues de tomar la escritura, dentro de la transaccion.
    nro = _siguiente_comprobante(db)
    db.execute(update(Venta).where(Venta.id == venta.id).values(nro_comprobante=nro)
               .execution_options(synchronize_session=False))

    # 3) La reserva termina con el cobro: se marca atendida y se libera lo que
    #    todavia retiene. Liberar es por linea ("reservado" -> "liberado"), asi
    #    que aunque alguien la haya atendido antes, no se libera dos veces.
    reserva_atendida, liberadas = False, 0
    if venta.reserva_id:
        marca = db.execute(
            update(Reserva).where(Reserva.id == venta.reserva_id, Reserva.estado.in_(reservas.ACTIVAS))
            .values(estado="atendida").execution_options(synchronize_session=False)
        )
        reserva_atendida = marca.rowcount == 1
        liberadas = reservas.liberar_stock(db, venta.reserva_id)

    # 4) Descuento condicionado a que el stock libre alcance, linea por linea.
    sucursal = db.get(Sucursal, venta.sucursal_id)
    movimientos = []
    for d in db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta.id).order_by(DetalleVenta.id).all():
        baja = db.execute(
            update(Inventario)
            .where(Inventario.variante_id == d.variante_id,
                   Inventario.sucursal_id == venta.sucursal_id,
                   Inventario.cantidad - Inventario.cantidad_reservada >= d.cantidad)
            .values(cantidad=Inventario.cantidad - d.cantidad)
            .execution_options(synchronize_session=False)
        )
        if baja.rowcount != 1:
            nombre = ventas.nombre_variante(*ventas._variante(db, d.variante_id))
            db.rollback()
            raise HTTPException(
                400, f"No se pudo cobrar: {nombre} ya no tiene {d.cantidad} unidades libres en "
                     f"{sucursal.nombre}. No se cobro nada y la venta sigue pendiente"
            )
        movimiento = MovimientoInventario(
            variante_id=d.variante_id, sucursal_id=venta.sucursal_id, usuario_id=usuario.id,
            tipo="salida", cantidad=d.cantidad, motivo=f"Venta #{venta.id} ({nro})",
        )
        db.add(movimiento)
        movimientos.append(movimiento)

    # 5) El pago queda registrado junto con todo lo anterior.
    if pago is None:
        pago = Pago(venta_id=venta.id, metodo=metodo, pasarela=pasarela, monto=monto,
                    moneda="BOB", estado="exitoso", referencia_externa=referencia)
        db.add(pago)
    else:
        pago.estado = "exitoso"
        pago.monto = monto
        if referencia:
            pago.referencia_externa = referencia
    db.commit()

    total = ventas.dinero(venta.total)
    return {
        "aprobado": True,
        "nro_comprobante": nro,
        "cambio": float(monto - total) if metodo == "efectivo" else 0.0,
        "reserva_atendida": reserva_atendida,
        "unidades_liberadas_de_reserva": liberadas,
        "movimientos": [{"id": m.id, "variante_id": m.variante_id, "tipo": m.tipo,
                         "cantidad": m.cantidad, "motivo": m.motivo} for m in movimientos],
        "pago": _salida_pago(pago),
        "venta": ventas.salida(db, db.get(Venta, venta.id)),
    }


def rechazar(db: Session, venta: Venta, *, metodo: str, pasarela: str | None,
             referencia: str | None, monto, motivo: str, pago: Pago | None = None) -> dict:
    """La pasarela no cobro: la venta vuelve al carrito y el inventario no se toca."""
    vuelve = db.execute(
        update(Venta).where(Venta.id == venta.id, Venta.estado == "pendiente")
        .values(estado="carrito").execution_options(synchronize_session=False)
    )
    if vuelve.rowcount != 1:
        db.rollback()
        raise HTTPException(400, _mensaje_estado(db.get(Venta, venta.id)))

    if pago is None:
        pago = Pago(venta_id=venta.id, metodo=metodo, pasarela=pasarela,
                    monto=ventas.dinero(monto), moneda="BOB", estado="fallido",
                    referencia_externa=referencia)
        db.add(pago)
    else:
        pago.estado = "fallido"
        if referencia:
            pago.referencia_externa = referencia
    db.commit()

    return {
        "aprobado": False,
        "motivo": f"{motivo}. La compra vuelve al carrito y no se toco el inventario",
        "pago": _salida_pago(pago),
        "venta": ventas.salida(db, db.get(Venta, venta.id)),
    }


# ==============================================================================
#  POST /api/pagos  -- caja (efectivo, tarjeta, QR) y tarjeta en linea (Stripe)
# ==============================================================================
def pagar(db: Session, usuario: Usuario, datos, personal: bool) -> dict:
    metodo = normalizar(datos.metodo)
    venta = _venta_cobrable(db, datos.venta_id)
    _validar_canal(venta, metodo)
    _autorizar(db, venta, usuario, personal, "pagar por la pasarela")

    total = ventas.dinero(venta.total)
    monto = ventas.dinero(datos.monto)
    if metodo == "efectivo":
        if monto < total:
            raise HTTPException(400, f"El monto (Bs {monto}) no cubre el total (Bs {total})")
    elif monto != total:
        raise HTTPException(400, f"Con {metodo} se cobra el total exacto: Bs {total}")

    if venta.canal == "caja":
        # El dinero ya cambio de manos en el mostrador: aqui solo se asienta.
        return confirmar_cobro(db, venta, usuario, metodo=metodo,
                               referencia=_referencia_local(), monto=monto)

    if metodo == "qr":
        raise HTTPException(400, "El QR se paga desde /api/pagos/qr: primero se genera y "
                                 "despues se consulta si el banco lo cobro")
    return _pagar_tarjeta(db, venta, usuario, datos, monto)


def _pagar_tarjeta(db: Session, venta: Venta, usuario: Usuario, datos, monto) -> dict:
    """Tarjeta en linea: el cobro lo resuelve Stripe en la misma llamada.

    Un rechazo (tarjeta declinada, sin fondos, o un numero que no corresponde a
    ninguna tarjeta de prueba) no es un error: devuelve la venta al carrito sin
    tocar el inventario y el cliente puede corregir y reintentar.
    """
    numero = datos.numero_tarjeta or ""
    try:
        cobro = stripe_gw.cobrar(venta.id, float(monto), f"GangaClothes venta #{venta.id}", numero)
    except http.ErrorPasarela as e:
        # No se pudo ni preguntar: la venta sigue pendiente para reintentar.
        raise HTTPException(502, f"No se pudo contactar a Stripe: {e.mensaje}") from e

    if not cobro.aprobado:
        return rechazar(db, venta, metodo="tarjeta", pasarela="stripe",
                        referencia=cobro.referencia, monto=monto,
                        motivo=cobro.motivo or "La pasarela rechazo la tarjeta")

    resultado = confirmar_cobro(db, venta, usuario, metodo="tarjeta", pasarela="stripe",
                                referencia=cobro.referencia, monto=monto)
    resultado["tarjeta"] = {"marca": cobro.marca, "ultimos4": cobro.ultimos4, "simulado": cobro.simulado}
    return resultado


# ==============================================================================
#  QR: generar, consultar y (solo en simulado) forzar el desenlace
# ==============================================================================
def _pago_qr_pendiente(db: Session, venta_id: int, qr_id: str | None = None) -> Pago | None:
    consulta = db.query(Pago).filter(Pago.venta_id == venta_id, Pago.metodo == "qr",
                                     Pago.estado == "pendiente")
    if qr_id:
        consulta = consulta.filter(Pago.referencia_externa == qr_id)
    return consulta.order_by(Pago.id.desc()).first()


def crear_qr(db: Session, usuario: Usuario, venta_id: int) -> dict:
    """Genera el QR de cobro de una venta en linea y lo deja registrado como pago pendiente."""
    venta = _venta_cobrable(db, venta_id)
    _validar_canal(venta, "qr")
    _autorizar(db, venta, usuario, False, "pagar con QR")

    # Si ya habia un QR vivo para esta venta se devuelve el mismo, en lugar de
    # generar otro que el cliente podria pagar por duplicado.
    anterior = _pago_qr_pendiente(db, venta.id)
    if anterior is not None:
        try:
            vigente = qr_bcp.consultar(anterior.referencia_externa, venta.id)
            if vigente.estado == qr_bcp.EN_COLA:
                return {"venta_id": venta.id, "pago_id": anterior.id, **vigente.a_dict()}
        except http.ErrorPasarela:
            # El anterior ya no se puede consultar (vencido o reinicio): se descarta.
            anterior.estado = "fallido"
            db.commit()

    total = ventas.dinero(venta.total)
    try:
        cobro = qr_bcp.generar(venta.id, float(total), f"GangaClothes venta #{venta.id}")
    except http.ErrorPasarela as e:
        raise HTTPException(502, f"No se pudo generar el QR: {e.mensaje}") from e

    pago = Pago(venta_id=venta.id, metodo="qr", pasarela="bcp_qr", monto=total, moneda="BOB",
                estado="pendiente", referencia_externa=cobro.id)
    db.add(pago)
    db.commit()
    return {"venta_id": venta.id, "pago_id": pago.id, **cobro.a_dict()}


def consultar_qr(db: Session, usuario: Usuario, venta_id: int, qr_id: str, personal: bool) -> dict:
    """Pregunta al banco como quedo el QR y, si se pago, cierra la venta.

    Es idempotente: consultar de nuevo una venta ya cobrada devuelve el mismo
    comprobante sin volver a descontar inventario.
    """
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(404, "Venta no encontrada")
    if venta.canal == "caja":
        raise HTTPException(400, "El QR en linea es para las compras web o movil")
    _autorizar(db, venta, usuario, personal, "consultar su pago por QR")

    pago = db.query(Pago).filter(Pago.venta_id == venta_id, Pago.referencia_externa == qr_id).first()
    if pago is None:
        raise HTTPException(404, f"El QR {qr_id} no corresponde a la venta #{venta_id}")

    # Ya se habia cobrado: se responde lo mismo, sin tocar nada.
    if venta.estado == "pagada" and pago.estado == "exitoso":
        return {"aprobado": True, "estado": qr_bcp.PROCESADO, "descripcion": "PROCESADO",
                "pendiente": False, "rechazado": False, "qr_id": qr_id,
                "nro_comprobante": venta.nro_comprobante, "pago": _salida_pago(pago),
                "venta": ventas.salida(db, venta)}

    try:
        cobro = qr_bcp.consultar(qr_id, venta_id)
    except http.ErrorPasarela as e:
        raise HTTPException(502, f"No se pudo consultar el QR: {e.mensaje}") from e

    salida = {**cobro.a_dict(), "venta_id": venta_id, "pago_id": pago.id}

    if cobro.aprobado:
        if venta.estado != "pendiente":
            raise HTTPException(400, _mensaje_estado(venta))
        resultado = confirmar_cobro(db, venta, usuario, metodo="qr", pasarela="bcp_qr",
                                    referencia=qr_id, monto=venta.total, pago=pago)
        return {**salida, **resultado}

    if cobro.rechazado:
        motivo = ("El QR vencio antes de que se pagara" if cobro.estado == qr_bcp.VENCIDO
                  else "El QR fue anulado")
        if venta.estado == "pendiente":
            resultado = rechazar(db, venta, metodo="qr", pasarela="bcp_qr", referencia=qr_id,
                                 monto=venta.total, motivo=motivo, pago=pago)
            return {**salida, **resultado}
        # El rechazo ya se habia procesado (la pantalla pregunta cada pocos
        # segundos y puede llegar dos veces). Se responde lo mismo, con el motivo
        # de verdad y no uno generico, para que el cliente entienda que paso.
        return {**salida, "aprobado": False,
                "motivo": f"{motivo}. Tu compra volvio al carrito y no se toco el inventario"}

    # Sigue en cola: el cliente todavia no lo escaneo.
    return {**salida, "aprobado": False}


def simular_qr(db: Session, usuario: Usuario, venta_id: int | None, qr_id: str,
               estado: str, personal: bool) -> dict:
    """Fuerza el desenlace de un QR simulado. Solo existe con BCP_MODO=simulado:
    es lo que permite demostrar 'pagado' y 'vencido' sin una banca movil.

    La pantalla del cliente no lo usa (no corresponde que vea botones de
    prueba): esto es para las pruebas automaticas y para una demostracion.
    """
    if qr_bcp.modo() != "simulado":
        raise HTTPException(400, "Forzar el estado de un QR solo se puede con BCP_MODO=simulado")

    if venta_id is None:
        # El QR ya sabe de que venta es: se busca por su referencia.
        pago = db.query(Pago).filter(Pago.referencia_externa == qr_id,
                                     Pago.metodo == "qr").order_by(Pago.id.desc()).first()
        if pago is None:
            raise HTTPException(404, f"No hay ningun cobro con el QR {qr_id}")
        venta_id = pago.venta_id

    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(404, "Venta no encontrada")
    _autorizar(db, venta, usuario, personal, "simular su pago por QR")
    try:
        qr_bcp.marcar_simulado(qr_id, estado, pagador=usuario.nombre)
    except http.ErrorPasarela as e:
        raise HTTPException(400, e.mensaje) from e
    return consultar_qr(db, usuario, venta_id, qr_id, personal)


# ==============================================================================
#  Consultas
# ==============================================================================
def metodos_disponibles(canal: str = "web") -> dict:
    """Que puede ofrecer hoy cada pantalla y en que estado esta cada pasarela."""
    stripe_estado = stripe_gw.estado_del_servicio()
    qr_estado = qr_bcp.estado_del_servicio()
    if canal == "caja":
        metodos = [{"valor": m, "etiqueta": ETIQUETAS[m], "disponible": True,
                    "pasarela": None, "detalle": "Se cobra en el mostrador"}
                   for m in ("efectivo", "tarjeta", "qr")]
    else:
        metodos = [
            {"valor": "tarjeta", "etiqueta": "Tarjeta de credito o debito",
             "disponible": stripe_estado["disponible"], "pasarela": "stripe",
             "detalle": stripe_estado["motivo"], "modo": stripe_estado["modo"],
             "clave_publica": stripe_estado["clave_publica"]},
            {"valor": "qr", "etiqueta": "QR simple (Banco de Credito de Bolivia)",
             "disponible": qr_estado["disponible"], "pasarela": "bcp_qr",
             "detalle": qr_estado["motivo"], "modo": qr_estado["modo"]},
        ]
    return {"canal": canal, "metodos": metodos}


def listar(db: Session, usuario: Usuario, venta_id: int | None, personal: bool) -> list[dict]:
    if not personal:
        # Un cliente solo consulta los pagos de una compra suya.
        if venta_id is None:
            raise HTTPException(400, "Indica venta_id para ver los pagos de tu compra")
        venta = db.get(Venta, venta_id)
        if venta is None:
            raise HTTPException(404, "Venta no encontrada")
        cliente = ventas.cliente_de(db, usuario, "ver pagos de sus compras")
        if venta.cliente_id != cliente.id:
            raise HTTPException(403, "Solo puedes ver los pagos de tus compras")

    consulta = db.query(Pago)
    if venta_id is not None:
        consulta = consulta.filter(Pago.venta_id == venta_id)
    return [_salida_pago(p) for p in consulta.order_by(Pago.fecha.desc(), Pago.id.desc()).all()]
