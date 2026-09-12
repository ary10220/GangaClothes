"""Ventas: carrito del cliente (CU17) y venta presencial en caja (CU14).

Crear una venta NUNCA toca el inventario. El stock se descuenta en un unico
lugar: al registrarse un pago exitoso (modulo pagos). Aqui solo se valida que
alcance, para no dejar armar compras imposibles; el carrito no aparta stock.
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Cliente, Usuario
from app.models.ventas import DetalleReserva, DetalleVenta, Pago, Reserva, Venta
from app.modules.reservas import service as reservas

ESTADOS = {"carrito", "pendiente", "pagada", "anulada"}
CANALES = {"web", "movil", "caja"}
CENTAVO = Decimal("0.01")


# ------------------------------------------------------------- utilidades
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


def _variante_vendible(db: Session, variante_id: int):
    fila = _variante(db, variante_id)
    if fila is None:
        raise HTTPException(404, f"La variante {variante_id} no existe")
    variante, prenda, _talla, _color = fila
    if variante.activo is False or prenda.activo is False:
        raise HTTPException(400, f"{nombre_variante(*fila)} ya no esta a la venta")
    return fila


def recalcular(db: Session, venta: Venta, refrescar_precios: bool = False) -> None:
    """Rehace subtotales y total desde las lineas. En el carrito el precio se
    actualiza al vigente: todavia no es una venta cerrada."""
    db.flush()
    subtotal = Decimal("0")
    for d in db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta.id).all():
        if refrescar_precios:
            fila = _variante(db, d.variante_id)
            if fila:
                d.precio_unitario = dinero(fila[1].precio_venta)
        d.subtotal = dinero(dinero(d.precio_unitario) * d.cantidad - dinero(d.descuento))
        subtotal += d.subtotal
    venta.subtotal = subtotal
    venta.descuento = dinero(venta.descuento)
    venta.total = subtotal - venta.descuento
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
    detalle = []
    for d, v, p, t, c in filas:
        item = {
            "id": d.id,
            "variante_id": d.variante_id,
            "sku": v.sku,
            "prenda": p.nombre,
            "talla": t.nombre,
            "color": c.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": float(dinero(d.precio_unitario)),
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
    return {
        "id": venta.id,
        "estado": venta.estado,
        "canal": venta.canal,
        "fecha": venta.fecha.isoformat() if venta.fecha else None,
        "sucursal_id": venta.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "cliente": cliente,
        "cajero": cajero,
        "reserva_id": venta.reserva_id,
        "unidades": sum(i["cantidad"] for i in detalle),
        "subtotal": float(dinero(venta.subtotal)),
        "descuento": float(dinero(venta.descuento)),
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


def abrir_carrito(db: Session, usuario: Usuario, sucursal_id: int | None = None) -> tuple[dict, bool]:
    cliente = cliente_de(db, usuario)
    if sucursal_id is not None:
        _sucursal_activa(db, sucursal_id)

    venta = _carrito_de(db, cliente)
    creado = venta is None
    if creado:
        sucursal = db.get(Sucursal, sucursal_id) if sucursal_id else _sucursal_por_defecto(db)
        venta = Venta(cliente_id=cliente.id, sucursal_id=sucursal.id, canal="web",
                      estado="carrito", subtotal=0, descuento=0, total=0)
        db.add(venta)
        db.commit()
    elif sucursal_id is not None and sucursal_id != venta.sucursal_id:
        venta.sucursal_id = sucursal_id
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

    fila = _variante_vendible(db, datos.variante_id)
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
    faltantes, precios = [], {}
    for variante_id, cantidad in lineas:
        fila = _variante_vendible(db, variante_id)
        alcanza = disponible(db, variante_id, datos.sucursal_id) + retenido.get(variante_id, 0)
        if cantidad > alcanza:
            faltantes.append(f"{nombre_variante(*fila)}: se venden {cantidad} y hay {alcanza}")
        precios[variante_id] = dinero(fila[1].precio_venta)
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
    for variante_id, cantidad in lineas:
        precio = precios[variante_id]
        db.add(DetalleVenta(venta_id=venta.id, variante_id=variante_id, cantidad=cantidad,
                            precio_unitario=precio, descuento=0, subtotal=precio * cantidad))
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
    total = dinero(venta.total)
    recibido = dinero(pago.monto) if pago else total
    return {
        "nro_comprobante": venta.nro_comprobante,
        "fecha": pago.fecha.isoformat() if pago and pago.fecha else None,
        "tienda": "GANGACLOTHES",
        "sucursal": {"nombre": sucursal.nombre, "direccion": sucursal.direccion} if sucursal else None,
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
            "subtotal": i["subtotal"],
        } for i in datos["detalle"]],
        "subtotal": datos["subtotal"],
        "descuento": datos["descuento"],
        "total": float(total),
        "moneda": pago.moneda if pago else "BOB",
        "pago": {
            "metodo": pago.metodo if pago else None,
            "recibido": float(recibido),
            "cambio": float(max(recibido - total, Decimal("0"))),
            "referencia_externa": pago.referencia_externa if pago else None,
        },
    }
