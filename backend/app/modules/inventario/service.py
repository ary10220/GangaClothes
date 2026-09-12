"""Reglas de inventario: stock por sucursal, movimientos y compras.

Toda operacion que toca el stock pasa por aqui, nunca desde el router, para
que la validacion y la escritura queden en la misma transaccion.
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.inventario import (Compra, DetalleCompra, Inventario,
                                   MovimientoInventario, Proveedor)
from app.models.sucursales import Sucursal

# Como afecta cada tipo al stock. El ajuste no suma ni resta: fija el total.
SUMAN = {"ingreso", "devolucion"}
RESTAN = {"salida"}
FIJAN = {"ajuste"}
TIPOS = SUMAN | RESTAN | FIJAN

ESTADOS_COMPRA = {"pendiente", "recibida", "anulada"}


# --------------------------------------------------------------- consultas
def _fila_inventario(inv: Inventario, variante, prenda, talla, color, sucursal) -> dict:
    disponible = inv.cantidad - inv.cantidad_reservada
    minimo = inv.stock_minimo or 0
    return {
        "id": inv.id,
        "variante_id": inv.variante_id,
        "sku": variante.sku if variante else None,
        "prenda": prenda.nombre if prenda else None,
        "talla": talla.nombre if talla else None,
        "color": color.nombre if color else None,
        "color_hex": color.codigo_hex if color else None,
        "sucursal_id": inv.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "cantidad": inv.cantidad,
        "cantidad_reservada": inv.cantidad_reservada,
        "disponible": disponible,
        "stock_minimo": minimo,
        "stock_maximo": inv.stock_maximo or 0,
        # La alerta se dispara al llegar al minimo, no al pasarlo de largo.
        "bajo_minimo": disponible <= minimo,
    }


def listar(db: Session, sucursal_id: int | None = None, solo_alertas: bool = False) -> list[dict]:
    consulta = (
        db.query(Inventario, Variante, Prenda, Talla, Color, Sucursal)
        .join(Variante, Variante.id == Inventario.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
    )
    if sucursal_id:
        consulta = consulta.filter(Inventario.sucursal_id == sucursal_id)

    filas = [_fila_inventario(*t) for t in consulta.order_by(Variante.sku).all()]
    return [f for f in filas if f["bajo_minimo"]] if solo_alertas else filas


# ------------------------------------------------------------ alta de stock
def crear_registro(db: Session, datos) -> dict:
    if db.get(Variante, datos.variante_id) is None:
        raise HTTPException(404, "La variante no existe")
    if db.get(Sucursal, datos.sucursal_id) is None:
        raise HTTPException(404, "La sucursal no existe")

    existe = (
        db.query(Inventario)
        .filter(Inventario.variante_id == datos.variante_id,
                Inventario.sucursal_id == datos.sucursal_id)
        .first()
    )
    if existe:
        raise HTTPException(400, "Esa variante ya tiene stock registrado en esa sucursal")

    _validar_limites(datos.stock_minimo, datos.stock_maximo)
    inv = Inventario(
        variante_id=datos.variante_id,
        sucursal_id=datos.sucursal_id,
        cantidad=datos.cantidad,
        cantidad_reservada=0,
        stock_minimo=datos.stock_minimo,
        stock_maximo=datos.stock_maximo,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return detalle(db, inv.id)


def _validar_limites(minimo: int, maximo: int) -> None:
    if minimo < 0 or maximo < 0:
        raise HTTPException(400, "El stock minimo y el maximo no pueden ser negativos")
    if maximo and minimo > maximo:
        raise HTTPException(
            400, f"El stock minimo ({minimo}) no puede ser mayor que el maximo ({maximo})"
        )


def actualizar_limites(db: Session, id: int, datos) -> dict:
    inv = db.get(Inventario, id)
    if inv is None:
        raise HTTPException(404, "Registro de inventario no encontrado")

    minimo = datos.stock_minimo if datos.stock_minimo is not None else (inv.stock_minimo or 0)
    maximo = datos.stock_maximo if datos.stock_maximo is not None else (inv.stock_maximo or 0)
    _validar_limites(minimo, maximo)

    inv.stock_minimo, inv.stock_maximo = minimo, maximo
    db.commit()
    return detalle(db, id)


def detalle(db: Session, id: int) -> dict:
    fila = (
        db.query(Inventario, Variante, Prenda, Talla, Color, Sucursal)
        .join(Variante, Variante.id == Inventario.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .filter(Inventario.id == id)
        .first()
    )
    if fila is None:
        raise HTTPException(404, "Registro de inventario no encontrado")
    return _fila_inventario(*fila)


# ------------------------------------------------------------- movimientos
def _stock_de(db: Session, variante_id: int, sucursal_id: int) -> Inventario:
    inv = (
        db.query(Inventario)
        .filter(Inventario.variante_id == variante_id, Inventario.sucursal_id == sucursal_id)
        .first()
    )
    if inv is None:
        raise HTTPException(
            404,
            "Esa variante no tiene stock registrado en esa sucursal. "
            "Crealo primero con POST /api/inventario",
        )
    return inv


def _aplicar(inv: Inventario, tipo: str, cantidad: int) -> None:
    """Cambia la cantidad en memoria; el commit lo hace quien llama."""
    if tipo in SUMAN:
        inv.cantidad += cantidad
    elif tipo in RESTAN:
        disponible = inv.cantidad - inv.cantidad_reservada
        if cantidad > disponible:
            raise HTTPException(
                400,
                f"No hay stock suficiente: se piden {cantidad} y solo hay {disponible} "
                f"disponibles ({inv.cantidad} en stock menos {inv.cantidad_reservada} reservados)",
            )
        inv.cantidad -= cantidad
    else:  # ajuste: la cantidad enviada es el total contado
        if cantidad < inv.cantidad_reservada:
            raise HTTPException(
                400,
                f"El ajuste deja {cantidad} unidades pero hay {inv.cantidad_reservada} reservadas",
            )
        inv.cantidad = cantidad


def registrar_movimiento(db: Session, datos, usuario_id: int | None) -> dict:
    if datos.tipo not in TIPOS:
        raise HTTPException(400, f"Tipo invalido. Use uno de: {', '.join(sorted(TIPOS))}")
    if datos.cantidad < 0:
        raise HTTPException(400, "La cantidad no puede ser negativa")
    if datos.cantidad == 0 and datos.tipo != "ajuste":
        raise HTTPException(400, "La cantidad debe ser mayor que cero")

    inv = _stock_de(db, datos.variante_id, datos.sucursal_id)
    antes = inv.cantidad
    _aplicar(inv, datos.tipo, datos.cantidad)

    movimiento = MovimientoInventario(
        variante_id=datos.variante_id,
        sucursal_id=datos.sucursal_id,
        usuario_id=usuario_id,
        tipo=datos.tipo,
        cantidad=datos.cantidad,
        motivo=datos.motivo,
    )
    db.add(movimiento)
    # El movimiento y el nuevo stock se guardan juntos: si algo falla, no queda
    # un movimiento sin su efecto ni un stock cambiado sin su comprobante.
    db.commit()
    db.refresh(movimiento)

    return {
        "movimiento": _fila_movimiento(db, movimiento),
        "stock_anterior": antes,
        "stock_actual": inv.cantidad,
        "inventario": detalle(db, inv.id),
    }


def _fila_movimiento(db: Session, m: MovimientoInventario) -> dict:
    variante = db.get(Variante, m.variante_id)
    sucursal = db.get(Sucursal, m.sucursal_id)
    prenda = db.get(Prenda, variante.prenda_id) if variante else None
    return {
        "id": m.id,
        "fecha": m.fecha.isoformat() if m.fecha else None,
        "tipo": m.tipo,
        "cantidad": m.cantidad,
        "motivo": m.motivo,
        "variante_id": m.variante_id,
        "sku": variante.sku if variante else None,
        "prenda": prenda.nombre if prenda else None,
        "sucursal_id": m.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "usuario_id": m.usuario_id,
    }


def listar_movimientos(db: Session, sucursal_id: int | None = None,
                       variante_id: int | None = None, limite: int = 200) -> list[dict]:
    consulta = db.query(MovimientoInventario)
    if sucursal_id:
        consulta = consulta.filter(MovimientoInventario.sucursal_id == sucursal_id)
    if variante_id:
        consulta = consulta.filter(MovimientoInventario.variante_id == variante_id)
    filas = (
        consulta.order_by(MovimientoInventario.fecha.desc(), MovimientoInventario.id.desc())
        .limit(limite)
        .all()
    )
    return [_fila_movimiento(db, m) for m in filas]


# ------------------------------------------------------------------ compras
def _fila_compra(db: Session, compra: Compra, con_detalle: bool = False) -> dict:
    proveedor = db.get(Proveedor, compra.proveedor_id)
    sucursal = db.get(Sucursal, compra.sucursal_id)
    salida = {
        "id": compra.id,
        "fecha": compra.fecha.isoformat() if compra.fecha else None,
        "estado": compra.estado,
        "total": float(compra.total or 0),
        "proveedor_id": compra.proveedor_id,
        "proveedor": proveedor.nombre if proveedor else None,
        "sucursal_id": compra.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
    }
    lineas = db.query(DetalleCompra).filter(DetalleCompra.compra_id == compra.id).all()
    salida["items"] = len(lineas)
    if con_detalle:
        salida["detalle"] = [_fila_detalle(db, d) for d in lineas]
    return salida


def _fila_detalle(db: Session, d: DetalleCompra) -> dict:
    variante = db.get(Variante, d.variante_id)
    prenda = db.get(Prenda, variante.prenda_id) if variante else None
    talla = db.get(Talla, variante.talla_id) if variante else None
    color = db.get(Color, variante.color_id) if variante else None
    return {
        "id": d.id,
        "variante_id": d.variante_id,
        "sku": variante.sku if variante else None,
        "prenda": prenda.nombre if prenda else None,
        "talla": talla.nombre if talla else None,
        "color": color.nombre if color else None,
        "cantidad": d.cantidad,
        "precio_unitario": float(d.precio_unitario),
        "subtotal": float(d.subtotal),
    }


def crear_compra(db: Session, datos) -> dict:
    if db.get(Proveedor, datos.proveedor_id) is None:
        raise HTTPException(404, "El proveedor no existe")
    if db.get(Sucursal, datos.sucursal_id) is None:
        raise HTTPException(404, "La sucursal no existe")
    if not datos.detalle:
        raise HTTPException(400, "La compra necesita al menos una linea de detalle")

    vistas = set()
    for linea in datos.detalle:
        if db.get(Variante, linea.variante_id) is None:
            raise HTTPException(404, f"La variante {linea.variante_id} no existe")
        if linea.cantidad <= 0:
            raise HTTPException(400, "La cantidad de cada linea debe ser mayor que cero")
        if linea.precio_unitario < 0:
            raise HTTPException(400, "El precio unitario no puede ser negativo")
        if linea.variante_id in vistas:
            raise HTTPException(400, f"La variante {linea.variante_id} esta repetida en el detalle")
        vistas.add(linea.variante_id)

    compra = Compra(proveedor_id=datos.proveedor_id, sucursal_id=datos.sucursal_id,
                    estado="pendiente", total=0)
    db.add(compra)
    db.flush()

    total = Decimal("0")
    for linea in datos.detalle:
        precio = Decimal(str(linea.precio_unitario))
        subtotal = precio * linea.cantidad
        total += subtotal
        db.add(DetalleCompra(compra_id=compra.id, variante_id=linea.variante_id,
                             cantidad=linea.cantidad, precio_unitario=precio, subtotal=subtotal))

    compra.total = total
    db.commit()
    db.refresh(compra)
    return _fila_compra(db, compra, con_detalle=True)


def listar_compras(db: Session, sucursal_id: int | None = None, estado: str | None = None) -> list[dict]:
    consulta = db.query(Compra)
    if sucursal_id:
        consulta = consulta.filter(Compra.sucursal_id == sucursal_id)
    if estado:
        if estado not in ESTADOS_COMPRA:
            raise HTTPException(400, f"Estado invalido. Use uno de: {', '.join(sorted(ESTADOS_COMPRA))}")
        consulta = consulta.filter(Compra.estado == estado)
    filas = consulta.order_by(Compra.fecha.desc(), Compra.id.desc()).all()
    return [_fila_compra(db, c) for c in filas]


def obtener_compra(db: Session, id: int) -> dict:
    compra = db.get(Compra, id)
    if compra is None:
        raise HTTPException(404, "Compra no encontrada")
    return _fila_compra(db, compra, con_detalle=True)


def recibir_compra(db: Session, id: int, usuario_id: int | None) -> dict:
    compra = db.get(Compra, id)
    if compra is None:
        raise HTTPException(404, "Compra no encontrada")
    if compra.estado == "recibida":
        raise HTTPException(400, "La compra ya fue recibida: no se puede recibir dos veces")
    if compra.estado == "anulada":
        raise HTTPException(400, "La compra esta anulada: no se puede recibir")

    lineas = db.query(DetalleCompra).filter(DetalleCompra.compra_id == compra.id).all()
    if not lineas:
        raise HTTPException(400, "La compra no tiene detalle: no hay nada que recibir")

    # Todo o nada: si una linea falla, ni el stock ni el estado quedan a medias.
    movimientos = []
    for linea in lineas:
        inv = (
            db.query(Inventario)
            .filter(Inventario.variante_id == linea.variante_id,
                    Inventario.sucursal_id == compra.sucursal_id)
            .first()
        )
        if inv is None:
            # La primera compra de una variante en una sucursal abre su stock.
            inv = Inventario(variante_id=linea.variante_id, sucursal_id=compra.sucursal_id,
                             cantidad=0, cantidad_reservada=0, stock_minimo=0, stock_maximo=0)
            db.add(inv)
            db.flush()
        inv.cantidad += linea.cantidad
        movimiento = MovimientoInventario(
            variante_id=linea.variante_id,
            sucursal_id=compra.sucursal_id,
            usuario_id=usuario_id,
            tipo="ingreso",
            cantidad=linea.cantidad,
            motivo=f"Recepcion de la compra #{compra.id}",
        )
        db.add(movimiento)
        movimientos.append(movimiento)

    compra.estado = "recibida"
    db.commit()

    return {
        "compra": _fila_compra(db, compra, con_detalle=True),
        "movimientos": [_fila_movimiento(db, m) for m in movimientos],
    }
