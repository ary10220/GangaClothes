"""Pagos (CU15) y pasarela simulada (CU17).

Este es el UNICO lugar donde se descuenta inventario por una venta. La regla
que impide descontar dos veces:

    UPDATE venta SET estado='pagada' WHERE id=:id AND estado='pendiente'

Solo si esa sentencia toca exactamente una fila se sigue adelante. Dos cobros
simultaneos de la misma venta no pueden pasar ambos: la base deja ganar a uno.
Comprobante, liberacion de la reserva, descuento, movimientos y el pago mismo
van en esa misma transaccion; si una linea no tiene stock, se revierte todo y
la venta sigue pendiente.
"""
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.models.inventario import Inventario, MovimientoInventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Usuario
from app.models.ventas import DetalleVenta, Pago, Reserva, Venta
from app.modules.reservas import service as reservas
from app.modules.ventas import service as ventas

METODOS = {"efectivo", "tarjeta", "qr", "pasarela"}
# En caja se cobra en mostrador; la compra en linea solo por la pasarela.
METODOS_POR_CANAL = {
    "caja": {"efectivo", "tarjeta", "qr"},
    "web": {"pasarela"},
    "movil": {"pasarela"},
}


def _referencia_stripe() -> str:
    """Identificador con la forma de un PaymentIntent de Stripe en modo prueba."""
    return f"pi_test_{uuid4().hex[:24]}"


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
        "monto": float(ventas.dinero(pago.monto)),
        "moneda": pago.moneda,
        "estado": pago.estado,
        "referencia_externa": pago.referencia_externa,
        "fecha": pago.fecha.isoformat() if pago.fecha else None,
    }


def _mensaje_estado(venta: Venta) -> str:
    if venta.estado == "pagada":
        return f"La venta #{venta.id} ya esta pagada (comprobante {venta.nro_comprobante}): no se cobra dos veces"
    if venta.estado == "carrito":
        return f"La venta #{venta.id} sigue en carrito: hay que confirmarla antes de pagar"
    return f"La venta #{venta.id} esta '{venta.estado}': no se puede cobrar"


def pagar(db: Session, usuario: Usuario, datos, personal: bool) -> dict:
    venta = db.get(Venta, datos.venta_id)
    if venta is None:
        raise HTTPException(404, "Venta no encontrada")

    metodo = datos.metodo.lower().strip()
    if metodo not in METODOS:
        raise HTTPException(400, f"Metodo invalido. Use uno de: {', '.join(sorted(METODOS))}")
    permitidos = METODOS_POR_CANAL.get(venta.canal, set())
    if metodo not in permitidos:
        raise HTTPException(
            400, f"Una venta por '{venta.canal}' se paga con: {', '.join(sorted(permitidos))}"
        )

    # Quien puede cobrar: la pasarela la usa el propio cliente; la caja, el personal.
    if metodo == "pasarela":
        cliente = ventas.cliente_de(db, usuario, "pagar por la pasarela")
        if venta.cliente_id != cliente.id:
            raise HTTPException(403, "Solo puedes pagar tus propias compras")
    elif not personal:
        raise HTTPException(403, "Tu rol no tiene el permiso necesario (pagos:crear)")

    if venta.estado != "pendiente":
        raise HTTPException(400, _mensaje_estado(venta))

    total = ventas.dinero(venta.total)
    monto = ventas.dinero(datos.monto)
    if metodo == "efectivo":
        if monto < total:
            raise HTTPException(400, f"El monto (Bs {monto}) no cubre el total (Bs {total})")
    elif monto != total:
        raise HTTPException(400, f"Con {metodo} se cobra el total exacto: Bs {total}")

    # ----------------------------------------------- pasarela: rechazo simulado
    if metodo == "pasarela" and datos.simular_fallo:
        vuelve = db.execute(
            update(Venta).where(Venta.id == venta.id, Venta.estado == "pendiente")
            .values(estado="carrito").execution_options(synchronize_session=False)
        )
        if vuelve.rowcount != 1:
            db.rollback()
            raise HTTPException(400, _mensaje_estado(db.get(Venta, venta.id)))
        pago = Pago(venta_id=venta.id, metodo="pasarela", pasarela="stripe", monto=monto,
                    moneda="BOB", estado="fallido", referencia_externa=_referencia_stripe())
        db.add(pago)
        db.commit()
        return {
            "aprobado": False,
            "motivo": "La pasarela rechazo la tarjeta (simulado: card_declined). "
                      "La compra vuelve al carrito y no se toco el inventario",
            "pago": _salida_pago(pago),
            "venta": ventas.salida(db, db.get(Venta, venta.id)),
        }

    # ----------------------------------------------------- cobro exitoso
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
    pago = Pago(
        venta_id=venta.id, metodo=metodo, pasarela="stripe" if metodo == "pasarela" else None,
        monto=monto, moneda="BOB", estado="exitoso",
        referencia_externa=_referencia_stripe() if metodo == "pasarela" else None,
    )
    db.add(pago)
    db.commit()

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
