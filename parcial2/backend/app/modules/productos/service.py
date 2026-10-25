from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...models import Categoria, Color, Producto, Proveedor, Talla, Temporada, Variante
from ..suscripciones.service import exigir_capacidad
from . import schemas


# ==============================================================================
# Helper functions
# ==============================================================================
def _get_producto_mio(db: Session, tenant_id: int, producto_id: int) -> Producto:
    p = db.query(Producto).filter(Producto.id == producto_id, Producto.tenant_id == tenant_id).first()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return p


def _get_variante_mia(db: Session, tenant_id: int, variante_id: int) -> Variante:
    v = db.query(Variante).filter(Variante.id == variante_id, Variante.tenant_id == tenant_id).first()
    if not v:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Variante no encontrada")
    return v


def _validar_relaciones(
    db: Session, tenant_id: int, categoria_id: int | None, temporada_id: int | None, proveedor_id: int | None
) -> None:
    if categoria_id is not None:
        cat = db.query(Categoria).filter(Categoria.id == categoria_id, Categoria.tenant_id == tenant_id).first()
        if not cat:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Categoria id {categoria_id} no existe en su empresa")

    if temporada_id is not None:
        temp = db.query(Temporada).filter(Temporada.id == temporada_id, Temporada.tenant_id == tenant_id).first()
        if not temp:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Temporada id {temporada_id} no existe en su empresa")

    if proveedor_id is not None:
        prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id, Proveedor.tenant_id == tenant_id).first()
        if not prov:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Proveedor id {proveedor_id} no existe en su empresa")


# ==============================================================================
# Producto CRUD
# ==============================================================================
def listar_productos(
    db: Session,
    tenant_id: int,
    categoria_id: int | None = None,
    temporada_id: int | None = None,
    proveedor_id: int | None = None,
    publicado: bool | None = None,
    activo: bool | None = None,
) -> list[Producto]:
    q = db.query(Producto).filter(Producto.tenant_id == tenant_id)
    if categoria_id is not None:
        q = q.filter(Producto.categoria_id == categoria_id)
    if temporada_id is not None:
        q = q.filter(Producto.temporada_id == temporada_id)
    if proveedor_id is not None:
        q = q.filter(Producto.proveedor_id == proveedor_id)
    if publicado is not None:
        q = q.filter(Producto.publicado == publicado)
    if activo is not None:
        q = q.filter(Producto.activo == activo)
    return q.order_by(Producto.id).all()


def crear_producto(db: Session, tenant_id: int, data: schemas.ProductoIn) -> Producto:
    # 1. Validar límite de productos del plan contratado (ej. Plan Básico max 100)
    exigir_capacidad(db, tenant_id, "productos")

    # 2. Validar que la categoria, temporada y proveedor pertenezcan a la empresa
    _validar_relaciones(db, tenant_id, data.categoria_id, data.temporada_id, data.proveedor_id)

    # 3. Validar duplicado de nombre en la misma empresa
    existe = (
        db.query(Producto)
        .filter(Producto.tenant_id == tenant_id, Producto.nombre == data.nombre)
        .first()
    )
    if existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe un producto con el nombre '{data.nombre}' en esta empresa",
        )

    producto = Producto(
        tenant_id=tenant_id,
        categoria_id=data.categoria_id,
        temporada_id=data.temporada_id,
        proveedor_id=data.proveedor_id,
        nombre=data.nombre,
        descripcion=data.descripcion,
        marca=data.marca,
        genero=data.genero,
        precio_venta=data.precio_venta,
        costo=data.costo,
        imagen_url=data.imagen_url,
        activo=data.activo,
        publicado=data.publicado,
    )
    db.add(producto)
    db.flush()

    # Variantes opcionales iniciales
    if data.variantes:
        for v_data in data.variantes:
            _crear_variante_interna(db, tenant_id, producto.id, v_data)

    db.commit()
    db.refresh(producto)
    return producto


def obtener_producto(db: Session, tenant_id: int, producto_id: int) -> Producto:
    return _get_producto_mio(db, tenant_id, producto_id)


def actualizar_producto(
    db: Session, tenant_id: int, producto_id: int, data: schemas.ProductoUpdateIn
) -> Producto:
    prod = _get_producto_mio(db, tenant_id, producto_id)
    payload = data.model_dump(exclude_unset=True)

    if "nombre" in payload and payload["nombre"] != prod.nombre:
        existe = (
            db.query(Producto)
            .filter(
                Producto.tenant_id == tenant_id,
                Producto.nombre == payload["nombre"],
                Producto.id != producto_id,
            )
            .first()
        )
        if existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un producto con el nombre '{payload['nombre']}' en esta empresa",
            )

    _validar_relaciones(
        db,
        tenant_id,
        payload.get("categoria_id"),
        payload.get("temporada_id"),
        payload.get("proveedor_id"),
    )

    for k, v in payload.items():
        setattr(prod, k, v)

    db.commit()
    db.refresh(prod)
    return prod


def eliminar_producto(db: Session, tenant_id: int, producto_id: int) -> None:
    prod = _get_producto_mio(db, tenant_id, producto_id)
    db.delete(prod)
    db.commit()


def cambiar_publicacion(db: Session, tenant_id: int, producto_id: int, publicado: bool) -> Producto:
    prod = _get_producto_mio(db, tenant_id, producto_id)
    prod.publicado = publicado
    db.commit()
    db.refresh(prod)
    return prod


# ==============================================================================
# Variante CRUD
# ==============================================================================
def _crear_variante_interna(
    db: Session, tenant_id: int, producto_id: int, data: schemas.VarianteIn
) -> Variante:
    # Validar talla y color
    talla = db.query(Talla).filter(Talla.id == data.talla_id, Talla.tenant_id == tenant_id).first()
    if not talla:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Talla id {data.talla_id} no encontrada en su empresa")

    color = db.query(Color).filter(Color.id == data.color_id, Color.tenant_id == tenant_id).first()
    if not color:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Color id {data.color_id} no encontrado en su empresa")

    # Validar combinacion unica para este producto
    comb_existe = (
        db.query(Variante)
        .filter(
            Variante.producto_id == producto_id,
            Variante.talla_id == data.talla_id,
            Variante.color_id == data.color_id,
        )
        .first()
    )
    if comb_existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Ya existe una variante con esa talla y color para este producto",
        )

    # SKU unico
    sku = data.sku or f"SKU-T{tenant_id}-P{producto_id}-T{data.talla_id}-C{data.color_id}"
    sku_existe = (
        db.query(Variante)
        .filter(Variante.tenant_id == tenant_id, Variante.sku == sku)
        .first()
    )
    if sku_existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe una variante con el SKU '{sku}' en esta empresa",
        )

    variante = Variante(
        tenant_id=tenant_id,
        producto_id=producto_id,
        talla_id=data.talla_id,
        color_id=data.color_id,
        sku=sku,
        precio_adicional=data.precio_adicional,
        imagen_url=data.imagen_url,
        activo=data.activo,
    )
    db.add(variante)
    return variante


def listar_variantes(db: Session, tenant_id: int, producto_id: int) -> list[Variante]:
    _get_producto_mio(db, tenant_id, producto_id)
    return (
        db.query(Variante)
        .filter(Variante.producto_id == producto_id, Variante.tenant_id == tenant_id)
        .order_by(Variante.id)
        .all()
    )


def crear_variante(
    db: Session, tenant_id: int, producto_id: int, data: schemas.VarianteIn
) -> Variante:
    _get_producto_mio(db, tenant_id, producto_id)
    v = _crear_variante_interna(db, tenant_id, producto_id, data)
    db.commit()
    db.refresh(v)
    return v


def obtener_variante(db: Session, tenant_id: int, variante_id: int) -> Variante:
    return _get_variante_mia(db, tenant_id, variante_id)


def actualizar_variante(
    db: Session, tenant_id: int, variante_id: int, data: schemas.VarianteUpdateIn
) -> Variante:
    v = _get_variante_mia(db, tenant_id, variante_id)
    payload = data.model_dump(exclude_unset=True)

    if "sku" in payload and payload["sku"] != v.sku:
        sku_existe = (
            db.query(Variante)
            .filter(
                Variante.tenant_id == tenant_id,
                Variante.sku == payload["sku"],
                Variante.id != variante_id,
            )
            .first()
        )
        if sku_existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe una variante con el SKU '{payload['sku']}' en esta empresa",
            )

    for k, v_val in payload.items():
        setattr(v, k, v_val)

    db.commit()
    db.refresh(v)
    return v


def eliminar_variante(db: Session, tenant_id: int, variante_id: int) -> None:
    v = _get_variante_mia(db, tenant_id, variante_id)
    db.delete(v)
    db.commit()
