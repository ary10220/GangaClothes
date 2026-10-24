"""Ventas: carrito del cliente (CU17) y venta presencial en caja (CU14).

Crear una venta NUNCA toca el inventario. El stock se descuenta en un unico
lugar: al registrarse un pago exitoso (modulo pagos). Aqui solo se valida que
alcance, para no dejar armar compras imposibles; el carrito no aparta stock.
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.fechas import texto_bolivia, utc_iso
from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.envios import Envio
from app.models.inventario import Inventario
from app.models.sucursales import Ciudad, Sucursal
from app.models.usuarios import Cliente, Usuario
from app.models.ventas import DetalleReserva, DetalleVenta, Pago, Promocion, Reserva, Venta
from app.modules.prendas.service import url_imagen
from app.modules.promociones import service as promociones
from app.modules.reservas import service as reservas

ESTADOS = {"carrito", "pendiente", "pagada", "anulada"}
CANALES = {"web", "movil", "caja"}
# Como recibe el cliente la compra (CU29). En caja siempre es "sucursal".
TIPOS_ENTREGA = {"sucursal", "delivery"}
CENTAVO = Decimal("0.01")


# ------------------------------------------------------------- utilidades
# El nombre legible del metodo se define aqui y no en `pagos` porque ese modulo
# ya importa este: al reves seria un ciclo.
_ETIQUETA_METODO = {"efectivo": "Efectivo", "tarjeta": "Tarjeta", "qr": "QR"}
_ETIQUETA_PASARELA = {"stripe": "Stripe", "bcp_qr": "BCP"}


def etiqueta_metodo(metodo: str | None, pasarela: str | None = None) -> str:
    base = _ETIQUETA_METODO.get(metodo or "", metodo or "—")
    proveedor = _ETIQUETA_PASARELA.get(pasarela or "")
    return f"{base} ({proveedor})" if proveedor else base


def dinero(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVO)


def cliente_de(db: Session, usuario: Usuario, accion: str = "comprar en la tienda en linea") -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
    if cliente is None:
        raise HTTPException(403, f"Solo los clientes pueden {accion}")
    return cliente


def _variante(db: Session, variante_id: int):
    return (
        db.query(Variante, Prenda, Talla, Color)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(Variante.id == variante_id)
        .first()
    )


def nombre_variante(variante, prenda, talla, color) -> str:
    return f"{variante.sku} ({prenda.nombre}, {talla.nombre}/{color.nombre})"


def disponible(db: Session, variante_id: int, sucursal_id: int) -> int:
    inv = (
        db.query(Inventario)
        .filter(Inventario.variante_id == variante_id, Inventario.sucursal_id == sucursal_id)
        .first()
    )
    return (inv.cantidad - inv.cantidad_reservada) if inv else 0


def _sucursal_activa(db: Session, sucursal_id: int) -> Sucursal:
    sucursal = db.get(Sucursal, sucursal_id)
    if sucursal is None:
        raise HTTPException(404, "La sucursal no existe")
    if sucursal.activo is False:
        raise HTTPException(400, f"La {sucursal.nombre} no esta vendiendo")
    return sucursal


def _sucursal_por_defecto(db: Session) -> Sucursal:
    sucursal = (
        db.query(Sucursal).filter(Sucursal.activo != False).order_by(Sucursal.id).first()  # noqa: E712
    )
    if sucursal is None:
        raise HTTPException(400, "No hay sucursales activas para despachar la compra")
    return sucursal


def _variante_vendible(db: Session, variante_id: int, en_linea: bool = False):
    """En caja basta con que la prenda este activa; en la tienda en linea ademas
    tiene que estar publicada."""
    fila = _variante(db, variante_id)
    if fila is None:
        raise HTTPException(404, f"La variante {variante_id} no existe")
    variante, prenda, _talla, _color = fila
    if variante.activo is False or prenda.activo is False:
        raise HTTPException(400, f"{nombre_variante(*fila)} ya no esta a la venta")
    if en_linea and not prenda.publicado:
        raise HTTPException(400, f"{nombre_variante(*fila)} no esta a la venta en la tienda en linea")
    return fila


def valorizar(db: Session, linea: DetalleVenta, prenda: Prenda, promos=None) -> None:
    """Pone en la linea el precio de lista y el descuento de la promocion vigente
    (CU18). `descuento` es el total de la linea, no por unidad."""
    if promos is None:
        promos = promociones.vigentes_por_prenda(db, [prenda.id]).get(prenda.id)
    calculo = promociones.aplicar(prenda.precio_venta, promos)
    linea.precio_unitario = calculo["precio_lista"]
    linea.descuento = dinero(calculo["descuento"] * linea.cantidad)
    linea.promocion_id = calculo["promocion"].id if calculo["promocion"] else None


def costo_envio_de(db: Session, venta: Venta, mercaderia: Decimal, hay_prendas: bool) -> Decimal:
    """Lo que se le suma al total por llevarle la compra a su casa (CU29).

    Mientras la compra no este pagada, el envio se recotiza en cada cambio del
    carrito: la distancia no cambia, pero cruzar el minimo de envio gratis si.
    Una vez pagada, el costo queda congelado en el que el cliente acepto.
    """
    if (venta.tipo_entrega or "sucursal") != "delivery":
        return Decimal("0")
    if venta.estado not in ("carrito", "pendiente"):
        return dinero(venta.costo_envio)
    # Importacion tardia a proposito: `envios` importa este modulo para el
    # dinero y la salida de la venta; al reves, arriba, seria un ciclo.
    from app.modules.envios import service as envios

    return envios.recotizar(db, venta, mercaderia, hay_prendas)


def recalcular(db: Session, venta: Venta, refrescar_precios: bool = False) -> None:
    """Rehace subtotales y total desde las lineas. En el carrito el precio y la
    promocion se actualizan a lo vigente: todavia no es una venta cerrada.

    venta.subtotal es la suma a precio de lista; venta.descuento, lo que rebajan
    las promociones; venta.costo_envio, lo que cuesta el delivery si lo hay; y
    venta.total, lo que se cobra:

        total = subtotal - descuento + costo_envio

    Cada linea guarda su neto, que nunca incluye el envio: el envio es de la
    compra entera, no de una prenda."""
    db.flush()
    lineas = db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta.id).all()
    if refrescar_precios and lineas:
        filas = {d.id: _variante(db, d.variante_id) for d in lineas}
        vigentes = promociones.vigentes_por_prenda(db, [f[1].id for f in filas.values() if f])
        for d in lineas:
            fila = filas[d.id]
            if fila:
                valorizar(db, d, fila[1], vigentes.get(fila[1].id, []))
    bruto, rebaja = Decimal("0"), Decimal("0")
    for d in lineas:
        importe = dinero(dinero(d.precio_unitario) * d.cantidad)
        d.descuento = min(dinero(d.descuento), importe)
        d.subtotal = importe - d.descuento
        bruto += importe
        rebaja += d.descuento
    venta.subtotal = bruto
    venta.descuento = rebaja
    venta.costo_envio = costo_envio_de(db, venta, bruto - rebaja, bool(lineas))
    venta.total = bruto - rebaja + venta.costo_envio
    db.flush()


def salida(db: Session, venta: Venta, con_stock: bool = False) -> dict:
    sucursal = db.get(Sucursal, venta.sucursal_id)
    filas = (
        db.query(DetalleVenta, Variante, Prenda, Talla, Color)
        .join(Variante, Variante.id == DetalleVenta.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(DetalleVenta.venta_id == venta.id)
        .order_by(DetalleVenta.id)
        .all()
    )
    nombres_promo = {}
    ids_promo = {d.promocion_id for d, *_ in filas if d.promocion_id}
    if ids_promo:
        nombres_promo = {pr.id: pr for pr in db.query(Promocion).filter(Promocion.id.in_(ids_promo)).all()}
    detalle = []
    for d, v, p, t, c in filas:
        promo = nombres_promo.get(d.promocion_id)
        rebaja = dinero(d.descuento)
        item = {
            "id": d.id,
            "variante_id": d.variante_id,
            "sku": v.sku,
            "prenda": p.nombre,
            "talla": t.nombre,
            "color": c.nombre,
            "cantidad": d.cantidad,
            "imagen_url": url_imagen(v.imagen_url or p.imagen_url),
            # precio_unitario es el de lista; precio_final, el de una unidad con su promocion.
            "precio_unitario": float(dinero(d.precio_unitario)),
            "precio_final": float(dinero(d.precio_unitario) - dinero(rebaja / d.cantidad)) if d.cantidad else 0.0,
            "descuento": float(rebaja),
            "promocion": ({"id": promo.id, "nombre": promo.nombre, "etiqueta": promociones.etiqueta(promo)}
                          if promo and rebaja > 0 else None),
            "subtotal": float(dinero(d.subtotal)),
        }
        if con_stock:
            disp = disponible(db, d.variante_id, venta.sucursal_id)
            item["disponible"] = disp
            item["alcanza"] = d.cantidad <= disp
        detalle.append(item)

    cliente = None
    if venta.cliente_id:
        cl = db.get(Cliente, venta.cliente_id)
        u = db.get(Usuario, cl.usuario_id) if cl else None
        cliente = {
            "id": venta.cliente_id,
            "nombre": " ".join(filter(None, [u.nombre, u.apellido])) if u else None,
            "email": u.email if u else None,
        }
    cajero = None
    if venta.cajero_id:
        u = db.get(Usuario, venta.cajero_id)
        if u:
            cajero = {"id": u.id, "nombre": " ".join(filter(None, [u.nombre, u.apellido]))}

    pagos = db.query(Pago).filter(Pago.venta_id == venta.id).order_by(Pago.id).all()
    # CU29: si la compra se entrega a domicilio, su envio viaja con ella. Campos
    # aditivos: la app movil, que solo hace retiro en sucursal, no cambia.
    envio = db.query(Envio).filter(Envio.venta_id == venta.id).first()
    return {
        "id": venta.id,
        "estado": venta.estado,
        "canal": venta.canal,
        "fecha": utc_iso(venta.fecha),
        "sucursal_id": venta.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "cliente": cliente,
        "cajero": cajero,
        "reserva_id": venta.reserva_id,
        "unidades": sum(i["cantidad"] for i in detalle),
        "subtotal": float(dinero(venta.subtotal)),
        "descuento": float(dinero(venta.descuento)),
        "tipo_entrega": venta.tipo_entrega or "sucursal",
        "costo_envio": float(dinero(venta.costo_envio)),
        "envio": {
            "id": envio.id,
            "estado": envio.estado,
            "direccion": envio.direccion,
            "referencia": envio.referencia,
            "telefono_contacto": envio.telefono_contacto,
            "latitud": envio.latitud,
            "longitud": envio.longitud,
            "distancia_km": float(dinero(envio.distancia_km)),
            "costo_envio": float(dinero(envio.costo_envio)),
            "express": bool(envio.express),
            "repartidor": envio.repartidor,
            "fecha_estimada": utc_iso(envio.fecha_estimada),
            "fecha_entrega": utc_iso(envio.fecha_entrega),
        } if envio else None,
        "total": float(dinero(venta.total)),
        "nro_comprobante": venta.nro_comprobante,
        "detalle": detalle,
        "pagos": [{
            "id": pg.id,
            "metodo": pg.metodo,
            "monto": float(dinero(pg.monto)),
            "estado": pg.estado,
            "referencia_externa": pg.referencia_externa,
        } for pg in pagos],
    }


# ------------------------------------------------------------ CU17 carrito
def _carrito_de(db: Session, cliente: Cliente) -> Venta | None:
    return (
        db.query(Venta)
        .filter(Venta.cliente_id == cliente.id, Venta.estado == "carrito",
                Venta.canal.in_(["web", "movil"]))
        .order_by(Venta.id.desc())
        .first()
    )


def _carrito_existente(db: Session, cliente: Cliente) -> Venta:
    venta = _carrito_de(db, cliente)
    if venta is None:
        raise HTTPException(404, "Todavia no tienes un carrito: crealo con POST /api/ventas/carrito")
    return venta


def abrir_carrito(db: Session, usuario: Usuario, sucursal_id: int | None = None,
                  canal: str | None = None) -> tuple[dict, bool]:
    """Un cliente tiene un solo carrito: si lo abre desde la app, pasa a canal
    "movil"; si no manda canal, se conserva el que tenia (por defecto "web")."""
    cliente = cliente_de(db, usuario)
    if sucursal_id is not None:
        _sucursal_activa(db, sucursal_id)
    if canal is not None and canal not in ("web", "movil"):
        raise HTTPException(400, "Canal invalido para la tienda en linea: use web o movil")

    venta = _carrito_de(db, cliente)
    creado = venta is None
    if creado:
        sucursal = db.get(Sucursal, sucursal_id) if sucursal_id else _sucursal_por_defecto(db)
        venta = Venta(cliente_id=cliente.id, sucursal_id=sucursal.id, canal=canal or "web",
                      estado="carrito", subtotal=0, descuento=0, total=0)
        db.add(venta)
        db.commit()
    else:
        cambio = False
        if sucursal_id is not None and sucursal_id != venta.sucursal_id:
            venta.sucursal_id = sucursal_id
            cambio = True
        if canal is not None and canal != venta.canal:
            venta.canal = canal
            cambio = True
        if cambio:
            # Cambiar de sucursal mueve el punto desde el que sale el delivery:
            # hay que rehacer la distancia y el costo del envio (CU29). Si la
            # sucursal nueva no llega hasta esa direccion, el envio se descarta
            # y la compra vuelve a retiro en sucursal (ver envios.recotizar).
            recalcular(db, venta, refrescar_precios=True)
            db.commit()
    return salida(db, db.get(Venta, venta.id), con_stock=True), creado


def ver_carrito(db: Session, usuario: Usuario) -> dict:
    venta = _carrito_existente(db, cliente_de(db, usuario))
    recalcular(db, venta, refrescar_precios=True)
    db.commit()
    return salida(db, db.get(Venta, venta.id), con_stock=True)


def agregar_item(db: Session, usuario: Usuario, datos) -> dict:
    cliente = cliente_de(db, usuario)
    venta = _carrito_de(db, cliente)
    if venta is None:
        venta = Venta(cliente_id=cliente.id, sucursal_id=_sucursal_por_defecto(db).id,
                      canal="web", estado="carrito", subtotal=0, descuento=0, total=0)
        db.add(venta)
        db.flush()

    fila = _variante_vendible(db, datos.variante_id, en_linea=True)
    variante, prenda, _t, _c = fila
    linea = (
        db.query(DetalleVenta)
        .filter(DetalleVenta.venta_id == venta.id, DetalleVenta.variante_id == datos.variante_id)
        .first()
    )
    total_pedido = (linea.cantidad if linea else 0) + datos.cantidad
    disp = disponible(db, datos.variante_id, venta.sucursal_id)
    if total_pedido > disp:
        sucursal = db.get(Sucursal, venta.sucursal_id)
        raise HTTPException(
            400, f"{nombre_variante(*fila)}: quieres {total_pedido} en total y hay {disp} "
                 f"disponibles en {sucursal.nombre}"
        )

    precio = dinero(prenda.precio_venta)
    if linea:
        linea.cantidad = total_pedido
    else:
        # recalcular() le pone enseguida el descuento de la promocion vigente.
        db.add(DetalleVenta(venta_id=venta.id, variante_id=variante.id, cantidad=datos.cantidad,
                            precio_unitario=precio, descuento=0, subtotal=precio * datos.cantidad))
    recalcular(db, venta, refrescar_precios=True)
    db.commit()
    return salida(db, db.get(Venta, venta.id), con_stock=True)


def _linea_del_carrito(db: Session, venta: Venta, item_id: int) -> DetalleVenta:
    linea = db.get(DetalleVenta, item_id)
    if linea is None or linea.venta_id != venta.id:
        raise HTTPException(404, "Ese item no esta en tu carrito")
    return linea


def cambiar_item(db: Session, usuario: Usuario, item_id: int, cantidad: int) -> dict:
    venta = _carrito_existente(db, cliente_de(db, usuario))
    linea = _linea_del_carrito(db, venta, item_id)
    disp = disponible(db, linea.variante_id, venta.sucursal_id)
    if cantidad > disp:
        fila = _variante(db, linea.variante_id)
        raise HTTPException(400, f"{nombre_variante(*fila)}: quieres {cantidad} y hay {disp} disponibles")
    linea.cantidad = cantidad
    recalcular(db, venta, refrescar_precios=True)
    db.commit()
    return salida(db, db.get(Venta, venta.id), con_stock=True)


def quitar_item(db: Session, usuario: Usuario, item_id: int) -> dict:
    venta = _carrito_existente(db, cliente_de(db, usuario))
    db.delete(_linea_del_carrito(db, venta, item_id))
    recalcular(db, venta, refrescar_precios=True)
    db.commit()
    return salida(db, db.get(Venta, venta.id), con_stock=True)


def confirmar(db: Session, usuario: Usuario) -> dict:
    venta = _carrito_existente(db, cliente_de(db, usuario))
    lineas = db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta.id).all()
    if not lineas:
        raise HTTPException(400, "El carrito esta vacio")

    faltantes = []
    for d in lineas:
        fila = _variante(db, d.variante_id)
        variante, prenda, _t, _c = fila
        # Pudo archivarse o despublicarse despues de agregarla al carrito.
        if variante.activo is False or prenda.activo is False or not prenda.publicado:
            faltantes.append(f"{nombre_variante(*fila)}: ya no esta a la venta en la tienda en linea")
            continue
        disp = disponible(db, d.variante_id, venta.sucursal_id)
        if d.cantidad > disp:
            faltantes.append(f"{nombre_variante(*_variante(db, d.variante_id))}: "
                             f"tienes {d.cantidad} y hay {disp} disponibles")
    if faltantes:
        raise HTTPException(400, "No se puede confirmar. " + "; ".join(faltantes))

    recalcular(db, venta, refrescar_precios=True)
    # Condicional: dos confirmaciones simultaneas no pueden pasar ambas.
    resultado = db.execute(
        update(Venta).where(Venta.id == venta.id, Venta.estado == "carrito")
        .values(estado="pendiente").execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        db.rollback()
        raise HTTPException(400, "El carrito ya fue confirmado")
    db.commit()
    return salida(db, db.get(Venta, venta.id))


# -------------------------------------------------------- CU14 presencial
def crear_presencial(db: Session, usuario: Usuario, datos) -> dict:
    _sucursal_activa(db, datos.sucursal_id)

    reserva = None
    retenido: dict[int, int] = {}
    if datos.reserva_id is not None:
        reserva = db.get(Reserva, datos.reserva_id)
        if reserva is None:
            raise HTTPException(404, "La reserva no existe")
        if reserva.sucursal_id != datos.sucursal_id:
            raise HTTPException(400, "La reserva es de otra sucursal")
        if reserva.estado not in reservas.ACTIVAS:
            raise HTTPException(
                400, f"La reserva esta '{reserva.estado}': solo se vende una reserva pendiente o preparada"
            )
        otra = (
            db.query(Venta)
            .filter(Venta.reserva_id == reserva.id, Venta.estado != "anulada")
            .first()
        )
        if otra:
            raise HTTPException(400, f"La reserva ya esta en la venta #{otra.id}")
        for d in (db.query(DetalleReserva)
                  .filter(DetalleReserva.reserva_id == reserva.id, DetalleReserva.estado == "reservado")
                  .all()):
            retenido[d.variante_id] = retenido.get(d.variante_id, 0) + d.cantidad

    if datos.detalle:
        lineas = [(l.variante_id, l.cantidad) for l in datos.detalle]
    elif reserva is not None:
        lineas = list(retenido.items())
    else:
        raise HTTPException(400, "La venta necesita al menos una prenda")
    if not lineas:
        raise HTTPException(400, "La reserva no tiene prendas retenidas para vender")

    ids = [vid for vid, _ in lineas]
    repetidas = sorted({i for i in ids if ids.count(i) > 1})
    if repetidas:
        raise HTTPException(400, f"Variantes repetidas en el detalle: {repetidas}")

    # Para esta venta cuenta como disponible lo libre MAS lo que su reserva retiene.
    faltantes, prendas = [], {}
    for variante_id, cantidad in lineas:
        fila = _variante_vendible(db, variante_id)
        alcanza = disponible(db, variante_id, datos.sucursal_id) + retenido.get(variante_id, 0)
        if cantidad > alcanza:
            faltantes.append(f"{nombre_variante(*fila)}: se venden {cantidad} y hay {alcanza}")
        prendas[variante_id] = fila[1]
    if faltantes:
        raise HTTPException(400, "No hay stock para la venta. " + "; ".join(faltantes))

    venta = Venta(
        cliente_id=reserva.cliente_id if reserva else None,
        sucursal_id=datos.sucursal_id,
        cajero_id=usuario.id,
        reserva_id=reserva.id if reserva else None,
        canal="caja",
        estado="pendiente",  # en caja se cobra enseguida: no pasa por carrito
        subtotal=0, descuento=0, total=0,
    )
    db.add(venta)
    db.flush()
    # CU18: en caja rige la misma promocion que en la tienda en linea. El precio y
    # el descuento quedan congelados en la venta desde este momento.
    vigentes = promociones.vigentes_por_prenda(db, [p.id for p in prendas.values()])
    for variante_id, cantidad in lineas:
        prenda = prendas[variante_id]
        linea = DetalleVenta(venta_id=venta.id, variante_id=variante_id, cantidad=cantidad,
                             precio_unitario=dinero(prenda.precio_venta), descuento=0, subtotal=0)
        valorizar(db, linea, prenda, vigentes.get(prenda.id, []))
        db.add(linea)
    recalcular(db, venta)
    db.commit()
    return salida(db, db.get(Venta, venta.id))


def listar(db: Session, sucursal_id: int | None = None, canal: str | None = None,
           estado: str | None = None) -> list[dict]:
    consulta = db.query(Venta)
    if sucursal_id:
        consulta = consulta.filter(Venta.sucursal_id == sucursal_id)
    if canal:
        if canal not in CANALES:
            raise HTTPException(400, f"Canal invalido. Use uno de: {', '.join(sorted(CANALES))}")
        consulta = consulta.filter(Venta.canal == canal)
    if estado:
        if estado not in ESTADOS:
            raise HTTPException(400, f"Estado invalido. Use uno de: {', '.join(sorted(ESTADOS))}")
        consulta = consulta.filter(Venta.estado == estado)
    return [salida(db, v) for v in consulta.order_by(Venta.fecha.desc(), Venta.id.desc()).all()]


def mias(db: Session, usuario: Usuario) -> list[dict]:
    """Devuelve solo las compras pagadas del cliente autenticado."""
    cliente = cliente_de(db, usuario, "consultar sus compras")
    ventas = (
        db.query(Venta)
        .filter(Venta.cliente_id == cliente.id, Venta.estado == "pagada")
        .order_by(Venta.fecha.desc(), Venta.id.desc())
        .all()
    )
    return [salida(db, venta) for venta in ventas]


# ------------------------------------------------------ CU15 comprobante
def comprobante(db: Session, usuario: Usuario, venta_id: int, personal: bool) -> dict:
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(404, "Venta no encontrada")
    if not personal:
        cliente = cliente_de(db, usuario, "ver comprobantes de sus compras")
        if venta.cliente_id != cliente.id:
            raise HTTPException(403, "Solo puedes ver los comprobantes de tus compras")
    if venta.estado != "pagada":
        raise HTTPException(400, f"La venta esta '{venta.estado}': solo una venta pagada tiene comprobante")

    pago = (
        db.query(Pago).filter(Pago.venta_id == venta.id, Pago.estado == "exitoso")
        .order_by(Pago.id.desc()).first()
    )
    datos = salida(db, venta)
    sucursal = db.get(Sucursal, venta.sucursal_id)
    ciudad = db.get(Ciudad, sucursal.ciudad_id) if sucursal else None
    total = dinero(venta.total)
    recibido = dinero(pago.monto) if pago else total
    # La fecha del comprobante es la del cobro; si por lo que sea no hay pago,
    # la de la venta. Se manda en UTC ("Z") y tambien escrita en hora de Bolivia,
    # que es la que se imprime en el papel.
    instante = (pago.fecha if pago else venta.fecha)
    return {
        "nro_comprobante": venta.nro_comprobante,
        "fecha": utc_iso(instante),
        "fecha_bolivia": texto_bolivia(utc_iso(instante)),
        "tienda": "GANGACLOTHES",
        "sucursal": {
            "nombre": sucursal.nombre,
            "direccion": sucursal.direccion,
            "telefono": sucursal.telefono,
            "horario": sucursal.horario,
            "ciudad": ciudad.nombre if ciudad else None,
        } if sucursal else None,
        "canal": venta.canal,
        "venta_id": venta.id,
        "reserva_id": venta.reserva_id,
        "cajero": datos["cajero"],
        "cliente": datos["cliente"],
        "items": [{
            "descripcion": f"{i['prenda']} {i['talla']}/{i['color']}",
            "sku": i["sku"],
            "cantidad": i["cantidad"],
            "precio_unitario": i["precio_unitario"],
            "descuento": i["descuento"],
            "promocion": i["promocion"]["nombre"] if i["promocion"] else None,
            "subtotal": i["subtotal"],
        } for i in datos["detalle"]],
        "subtotal": datos["subtotal"],
        "descuento": datos["descuento"],
        # CU29: si se entrego a domicilio, el comprobante dice adonde fue y
        # cuanto se cobro por llevarlo. En retiro en sucursal, `entrega` es None
        # y el costo es 0: el ticket queda exactamente igual que antes.
        "costo_envio": datos["costo_envio"],
        "entrega": ({
            "tipo": "delivery",
            "direccion": datos["envio"]["direccion"],
            "referencia": datos["envio"]["referencia"],
            "telefono": datos["envio"]["telefono_contacto"],
            "distancia_km": datos["envio"]["distancia_km"],
            "express": datos["envio"]["express"],
            "estado": datos["envio"]["estado"],
            "repartidor": datos["envio"]["repartidor"],
        } if datos["envio"] else None),
        "total": float(total),
        "moneda": pago.moneda if pago else "BOB",
        "pago": {
            "metodo": pago.metodo if pago else None,
            "pasarela": pago.pasarela if pago else None,
            "etiqueta": etiqueta_metodo(pago.metodo, pago.pasarela) if pago else "—",
            "recibido": float(recibido),
            "cambio": float(max(recibido - total, Decimal("0"))),
            "referencia_externa": pago.referencia_externa if pago else None,
        },
    }
