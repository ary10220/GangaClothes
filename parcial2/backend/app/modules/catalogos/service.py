from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...models import Categoria, Color, Talla, Temporada
from . import schemas


# ==============================================================================
# Categorias Service
# ==============================================================================
def _get_categoria_mia(db: Session, tenant_id: int, categoria_id: int) -> Categoria:
    c = db.query(Categoria).filter(Categoria.id == categoria_id, Categoria.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoria no encontrada")
    return c


def listar_categorias(db: Session, tenant_id: int) -> list[Categoria]:
    return db.query(Categoria).filter(Categoria.tenant_id == tenant_id).order_by(Categoria.id).all()


def crear_categoria(db: Session, tenant_id: int, data: schemas.CategoriaIn) -> Categoria:
    existe = (
        db.query(Categoria)
        .filter(Categoria.tenant_id == tenant_id, Categoria.nombre == data.nombre)
        .first()
    )
    if existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe una categoria con el nombre '{data.nombre}'",
        )

    cat = Categoria(
        tenant_id=tenant_id,
        nombre=data.nombre,
        descripcion=data.descripcion,
        activo=data.activo,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def obtener_categoria(db: Session, tenant_id: int, categoria_id: int) -> Categoria:
    return _get_categoria_mia(db, tenant_id, categoria_id)


def actualizar_categoria(
    db: Session, tenant_id: int, categoria_id: int, data: schemas.CategoriaUpdateIn
) -> Categoria:
    cat = _get_categoria_mia(db, tenant_id, categoria_id)
    payload = data.model_dump(exclude_unset=True)

    if "nombre" in payload and payload["nombre"] != cat.nombre:
        existe = (
            db.query(Categoria)
            .filter(
                Categoria.tenant_id == tenant_id,
                Categoria.nombre == payload["nombre"],
                Categoria.id != categoria_id,
            )
            .first()
        )
        if existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe una categoria con el nombre '{payload['nombre']}'",
            )

    for k, v in payload.items():
        setattr(cat, k, v)

    db.commit()
    db.refresh(cat)
    return cat


def eliminar_categoria(db: Session, tenant_id: int, categoria_id: int) -> None:
    cat = _get_categoria_mia(db, tenant_id, categoria_id)
    db.delete(cat)
    db.commit()


# ==============================================================================
# Tallas Service
# ==============================================================================
def _get_talla_mia(db: Session, tenant_id: int, talla_id: int) -> Talla:
    t = db.query(Talla).filter(Talla.id == talla_id, Talla.tenant_id == tenant_id).first()
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Talla no encontrada")
    return t


def listar_tallas(db: Session, tenant_id: int) -> list[Talla]:
    return db.query(Talla).filter(Talla.tenant_id == tenant_id).order_by(Talla.orden, Talla.id).all()


def crear_talla(db: Session, tenant_id: int, data: schemas.TallaIn) -> Talla:
    existe = (
        db.query(Talla)
        .filter(Talla.tenant_id == tenant_id, Talla.nombre == data.nombre)
        .first()
    )
    if existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe una talla con el nombre '{data.nombre}'",
        )

    talla = Talla(
        tenant_id=tenant_id,
        nombre=data.nombre,
        orden=data.orden,
        activo=data.activo,
    )
    db.add(talla)
    db.commit()
    db.refresh(talla)
    return talla


def obtener_talla(db: Session, tenant_id: int, talla_id: int) -> Talla:
    return _get_talla_mia(db, tenant_id, talla_id)


def actualizar_talla(
    db: Session, tenant_id: int, talla_id: int, data: schemas.TallaUpdateIn
) -> Talla:
    talla = _get_talla_mia(db, tenant_id, talla_id)
    payload = data.model_dump(exclude_unset=True)

    if "nombre" in payload and payload["nombre"] != talla.nombre:
        existe = (
            db.query(Talla)
            .filter(
                Talla.tenant_id == tenant_id,
                Talla.nombre == payload["nombre"],
                Talla.id != talla_id,
            )
            .first()
        )
        if existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe una talla con el nombre '{payload['nombre']}'",
            )

    for k, v in payload.items():
        setattr(talla, k, v)

    db.commit()
    db.refresh(talla)
    return talla


def eliminar_talla(db: Session, tenant_id: int, talla_id: int) -> None:
    talla = _get_talla_mia(db, tenant_id, talla_id)
    db.delete(talla)
    db.commit()


# ==============================================================================
# Colores Service
# ==============================================================================
def _get_color_mio(db: Session, tenant_id: int, color_id: int) -> Color:
    c = db.query(Color).filter(Color.id == color_id, Color.tenant_id == tenant_id).first()
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Color no encontrado")
    return c


def listar_colores(db: Session, tenant_id: int) -> list[Color]:
    return db.query(Color).filter(Color.tenant_id == tenant_id).order_by(Color.id).all()


def crear_color(db: Session, tenant_id: int, data: schemas.ColorIn) -> Color:
    existe = (
        db.query(Color)
        .filter(Color.tenant_id == tenant_id, Color.nombre == data.nombre)
        .first()
    )
    if existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe un color con el nombre '{data.nombre}'",
        )

    color = Color(
        tenant_id=tenant_id,
        nombre=data.nombre,
        codigo_hex=data.codigo_hex,
        activo=data.activo,
    )
    db.add(color)
    db.commit()
    db.refresh(color)
    return color


def obtener_color(db: Session, tenant_id: int, color_id: int) -> Color:
    return _get_color_mio(db, tenant_id, color_id)


def actualizar_color(
    db: Session, tenant_id: int, color_id: int, data: schemas.ColorUpdateIn
) -> Color:
    color = _get_color_mio(db, tenant_id, color_id)
    payload = data.model_dump(exclude_unset=True)

    if "nombre" in payload and payload["nombre"] != color.nombre:
        existe = (
            db.query(Color)
            .filter(
                Color.tenant_id == tenant_id,
                Color.nombre == payload["nombre"],
                Color.id != color_id,
            )
            .first()
        )
        if existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un color con el nombre '{payload['nombre']}'",
            )

    for k, v in payload.items():
        setattr(color, k, v)

    db.commit()
    db.refresh(color)
    return color


def eliminar_color(db: Session, tenant_id: int, color_id: int) -> None:
    color = _get_color_mio(db, tenant_id, color_id)
    db.delete(color)
    db.commit()


# ==============================================================================
# Temporadas Service
# ==============================================================================
def _get_temporada_mia(db: Session, tenant_id: int, temporada_id: int) -> Temporada:
    t = db.query(Temporada).filter(Temporada.id == temporada_id, Temporada.tenant_id == tenant_id).first()
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Temporada no encontrada")
    return t


def listar_temporadas(db: Session, tenant_id: int) -> list[Temporada]:
    return db.query(Temporada).filter(Temporada.tenant_id == tenant_id).order_by(Temporada.id).all()


def crear_temporada(db: Session, tenant_id: int, data: schemas.TemporadaIn) -> Temporada:
    existe = (
        db.query(Temporada)
        .filter(Temporada.tenant_id == tenant_id, Temporada.nombre == data.nombre)
        .first()
    )
    if existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe una temporada con el nombre '{data.nombre}'",
        )

    temporada = Temporada(
        tenant_id=tenant_id,
        nombre=data.nombre,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin,
        activo=data.activo,
    )
    db.add(temporada)
    db.commit()
    db.refresh(temporada)
    return temporada


def obtener_temporada(db: Session, tenant_id: int, temporada_id: int) -> Temporada:
    return _get_temporada_mia(db, tenant_id, temporada_id)


def actualizar_temporada(
    db: Session, tenant_id: int, temporada_id: int, data: schemas.TemporadaUpdateIn
) -> Temporada:
    temporada = _get_temporada_mia(db, tenant_id, temporada_id)
    payload = data.model_dump(exclude_unset=True)

    if "nombre" in payload and payload["nombre"] != temporada.nombre:
        existe = (
            db.query(Temporada)
            .filter(
                Temporada.tenant_id == tenant_id,
                Temporada.nombre == payload["nombre"],
                Temporada.id != temporada_id,
            )
            .first()
        )
        if existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe una temporada con el nombre '{payload['nombre']}'",
            )

    for k, v in payload.items():
        setattr(temporada, k, v)

    db.commit()
    db.refresh(temporada)
    return temporada


def eliminar_temporada(db: Session, tenant_id: int, temporada_id: int) -> None:
    temporada = _get_temporada_mia(db, tenant_id, temporada_id)
    db.delete(temporada)
    db.commit()
