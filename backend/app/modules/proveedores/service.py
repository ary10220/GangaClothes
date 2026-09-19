"""CU9 Informar productos disponibles (portal del proveedor).

El proveedor sale del token: su cuenta esta enlazada a una fila de `proveedor`
(proveedor.usuario_id) y solo puede tocar SU oferta. El personal de la tienda
la consulta, sin poder modificarla, al armar una compra (CU10).
"""
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.fechas import utc_iso
from app.models.catalogo import Categoria, Prenda, Temporada
from app.models.inventario import (DetalleCompra, ProductoProveedor, ProductoProveedorTemporada,
                                   Proveedor)
from app.models.usuarios import Usuario


# ---------------------------------------------------------------- identidad
def proveedor_de(db: Session, usuario: Usuario) -> Proveedor:
    proveedor = db.query(Proveedor).filter(Proveedor.usuario_id == usuario.id).first()
    if proveedor is None:
        raise HTTPException(
            403, "Tu cuenta todavia no esta enlazada a un proveedor. Pedile al administrador "
                 "que la enlace desde la pantalla de usuarios")
    if proveedor.activo is False:
        raise HTTPException(403, f"El proveedor '{proveedor.nombre}' esta dado de baja en la tienda")
    return proveedor


def perfil(db: Session, usuario: Usuario) -> dict:
    p = proveedor_de(db, usuario)
    productos = db.query(ProductoProveedor).filter(ProductoProveedor.proveedor_id == p.id)
    ultima = productos.order_by(ProductoProveedor.fecha_actualizacion.desc()).first()
    return {
        "id": p.id, "nombre": p.nombre, "nit": p.nit, "contacto": p.contacto,
        "telefono": p.telefono, "email": p.email, "direccion": p.direccion,
        "productos": productos.count(),
        "disponibles": productos.filter(ProductoProveedor.disponible.isnot(False)).count(),
        "ultima_actualizacion": utc_iso(ultima.fecha_actualizacion) if ultima else None,
    }


def enlazar_usuario(db: Session, usuario_id: int, proveedor_id: int | None) -> None:
    """Deja la cuenta enlazada a ese proveedor (o a ninguno). Lo usa el modulo de
    usuarios; el commit lo hace quien llama."""
    for actual in db.query(Proveedor).filter(Proveedor.usuario_id == usuario_id).all():
        if actual.id != proveedor_id:
            actual.usuario_id = None
    if proveedor_id is None:
        return
    proveedor = db.get(Proveedor, proveedor_id)
    if proveedor is None:
        raise HTTPException(400, "El proveedor elegido no existe")
    if proveedor.usuario_id not in (None, usuario_id):
        otro = db.get(Usuario, proveedor.usuario_id)
        raise HTTPException(
            400, f"'{proveedor.nombre}' ya tiene una cuenta enlazada"
                 + (f" ({otro.email})" if otro else "") + ": un proveedor usa una sola cuenta")
    proveedor.usuario_id = usuario_id


def proveedor_del_usuario(db: Session, usuario_id: int) -> dict | None:
    p = db.query(Proveedor).filter(Proveedor.usuario_id == usuario_id).first()
    return {"id": p.id, "nombre": p.nombre} if p else None


# ------------------------------------------------------------------- salida
def _salidas(db: Session, productos: list[ProductoProveedor]) -> list[dict]:
    if not productos:
        return []
    ids = [p.id for p in productos]
    temporadas = {t.id: t for t in db.query(Temporada).all()}
    categorias = {c.id: c.nombre for c in db.query(Categoria).all()}
    proveedores = {p.id: p.nombre for p in db.query(Proveedor).all()}
    ids_prenda = {p.prenda_id for p in productos if p.prenda_id}
    prendas = ({x.id: x for x in db.query(Prenda).filter(Prenda.id.in_(ids_prenda)).all()}
               if ids_prenda else {})
    por_producto: dict[int, list[int]] = {}
    for fila in (db.query(ProductoProveedorTemporada)
                 .filter(ProductoProveedorTemporada.producto_id.in_(ids)).all()):
        por_producto.setdefault(fila.producto_id, []).append(fila.temporada_id)

    salida = []
    for p in productos:
        ts = sorted((temporadas[i] for i in por_producto.get(p.id, []) if i in temporadas),
                    key=lambda t: t.nombre)
        salida.append({
            "id": p.id,
            "proveedor_id": p.proveedor_id,
            "proveedor": proveedores.get(p.proveedor_id),
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "categoria_id": p.categoria_id,
            "categoria": categorias.get(p.categoria_id),
            # Correspondencia con el catalogo de la tienda (la define su personal).
            "prenda_id": p.prenda_id,
            "prenda": prendas[p.prenda_id].nombre if p.prenda_id in prendas else None,
            "precio_referencial": float(p.precio_referencial),
            "cantidad_minima": p.cantidad_minima or 1,
            "disponible": p.disponible is not False,
            "temporada_ids": [t.id for t in ts],
            "temporadas": [{"id": t.id, "nombre": t.nombre} for t in ts],
            "fecha_actualizacion": utc_iso(p.fecha_actualizacion),
        })
    return salida


def mia(db: Session, usuario: Usuario) -> list[dict]:
    proveedor = proveedor_de(db, usuario)
    productos = (db.query(ProductoProveedor)
                 .filter(ProductoProveedor.proveedor_id == proveedor.id)
                 .order_by(ProductoProveedor.nombre).all())
    # A que prenda de su catalogo lo asocio la tienda es dato interno de la tienda.
    return [{k: v for k, v in p.items() if k not in ("prenda_id", "prenda")}
            for p in _salidas(db, productos)]


def consultar(db: Session, proveedor_id: int | None = None, temporada_id: int | None = None,
              q: str | None = None, solo_disponibles: bool = True) -> list[dict]:
    """Lo que ve el personal de la tienda al armar una compra."""
    consulta = (db.query(ProductoProveedor)
                .join(Proveedor, Proveedor.id == ProductoProveedor.proveedor_id)
                .filter(Proveedor.activo.isnot(False)))
    if proveedor_id:
        consulta = consulta.filter(ProductoProveedor.proveedor_id == proveedor_id)
    if solo_disponibles:
        consulta = consulta.filter(ProductoProveedor.disponible.isnot(False))
    if q:
        consulta = consulta.filter(ProductoProveedor.nombre.ilike(f"%{q.strip()}%"))
    if temporada_id:
        consulta = consulta.join(
            ProductoProveedorTemporada, ProductoProveedorTemporada.producto_id == ProductoProveedor.id
        ).filter(ProductoProveedorTemporada.temporada_id == temporada_id)
    return _salidas(db, consulta.order_by(Proveedor.nombre, ProductoProveedor.nombre).all())


def asociar_prenda(db: Session, producto_id: int, prenda_id: int | None) -> dict:
    """El personal de la tienda dice a que prenda de su catalogo corresponde un
    producto ofrecido (o le quita la correspondencia con prenda_id nulo)."""
    producto = db.get(ProductoProveedor, producto_id)
    if producto is None:
        raise HTTPException(404, "Ese producto no esta en la oferta de ningun proveedor")
    if prenda_id is not None:
        prenda = db.get(Prenda, prenda_id)
        if prenda is None:
            raise HTTPException(400, "La prenda elegida no existe")
        if prenda.activo is False:
            raise HTTPException(400, f"'{prenda.nombre}' esta archivada: no se le asocian productos")
    producto.prenda_id = prenda_id
    db.commit()
    return _salidas(db, [db.get(ProductoProveedor, producto.id)])[0]


# ---------------------------------------------------------------- escritura
def _validar(db: Session, producto: ProductoProveedor, temporada_ids: list[int]) -> list[int]:
    producto.nombre = (producto.nombre or "").strip()
    if not producto.nombre:
        raise HTTPException(400, "El nombre del producto es obligatorio")
    producto.descripcion = (producto.descripcion or "").strip() or None
    if Decimal(str(producto.precio_referencial)) <= 0:
        raise HTTPException(400, "El precio referencial debe ser mayor que cero")
    if (producto.cantidad_minima or 1) < 1:
        raise HTTPException(400, "La cantidad minima de pedido es al menos 1")
    if producto.categoria_id is not None and db.get(Categoria, producto.categoria_id) is None:
        raise HTTPException(400, "La categoria elegida no existe")

    ids = list(dict.fromkeys(temporada_ids))
    if ids:
        existentes = {t.id for t in db.query(Temporada).filter(Temporada.id.in_(ids)).all()}
        faltan = [i for i in ids if i not in existentes]
        if faltan:
            raise HTTPException(400, f"Temporadas inexistentes: {faltan}")

    repetido = (db.query(ProductoProveedor)
                .filter(ProductoProveedor.proveedor_id == producto.proveedor_id,
                        ProductoProveedor.nombre.ilike(producto.nombre),
                        ProductoProveedor.id != (producto.id or 0))
                .first())
    if repetido:
        raise HTTPException(400, f"Ya tienes un producto llamado '{repetido.nombre}': actualiza ese")
    return ids


def _asociar(db: Session, producto: ProductoProveedor, ids: list[int]) -> None:
    actuales = {f.temporada_id: f for f in db.query(ProductoProveedorTemporada)
                .filter(ProductoProveedorTemporada.producto_id == producto.id).all()}
    for temporada_id, fila in actuales.items():
        if temporada_id not in ids:
            db.delete(fila)
    for temporada_id in ids:
        if temporada_id not in actuales:
            db.add(ProductoProveedorTemporada(producto_id=producto.id, temporada_id=temporada_id))


def _mio(db: Session, usuario: Usuario, producto_id: int) -> ProductoProveedor:
    proveedor = proveedor_de(db, usuario)
    producto = db.get(ProductoProveedor, producto_id)
    # 404 y no 403: un proveedor no tiene por que saber que ids usan los demas.
    if producto is None or producto.proveedor_id != proveedor.id:
        raise HTTPException(404, "Ese producto no esta en tu oferta")
    return producto


def crear(db: Session, usuario: Usuario, datos) -> dict:
    proveedor = proveedor_de(db, usuario)
    producto = ProductoProveedor(proveedor_id=proveedor.id, fecha_actualizacion=datetime.utcnow(),
                                 **datos.model_dump(exclude={"temporada_ids"}))
    ids = _validar(db, producto, datos.temporada_ids)
    db.add(producto)
    db.flush()
    _asociar(db, producto, ids)
    db.commit()
    return _salidas(db, [db.get(ProductoProveedor, producto.id)])[0]


def editar(db: Session, usuario: Usuario, producto_id: int, datos) -> dict:
    producto = _mio(db, usuario, producto_id)
    cambios = datos.model_dump(exclude_unset=True)
    temporada_ids = cambios.pop("temporada_ids", None)
    for clave, valor in cambios.items():
        if valor is None and clave not in ("descripcion", "categoria_id"):
            continue
        setattr(producto, clave, valor)
    if temporada_ids is None:
        temporada_ids = [f.temporada_id for f in db.query(ProductoProveedorTemporada)
                         .filter(ProductoProveedorTemporada.producto_id == producto.id).all()]
    ids = _validar(db, producto, temporada_ids)
    _asociar(db, producto, ids)
    producto.fecha_actualizacion = datetime.utcnow()
    db.commit()
    return _salidas(db, [db.get(ProductoProveedor, producto.id)])[0]


def eliminar(db: Session, usuario: Usuario, producto_id: int) -> tuple[str, bool]:
    """Devuelve (nombre, quitado). Un producto del que ya partio alguna compra no
    se borra, para que esa compra siga diciendo que se pidio: queda sin disponibilidad."""
    producto = _mio(db, usuario, producto_id)
    nombre = producto.nombre
    if db.query(DetalleCompra.id).filter(DetalleCompra.producto_proveedor_id == producto.id).first():
        producto.disponible = False
        producto.fecha_actualizacion = datetime.utcnow()
        db.commit()
        return nombre, False
    db.query(ProductoProveedorTemporada).filter(
        ProductoProveedorTemporada.producto_id == producto.id).delete()
    db.delete(producto)
    db.commit()
    return nombre, True
