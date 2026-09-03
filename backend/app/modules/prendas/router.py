"""CU7 (admin de prendas/variantes) y CU16/CU22 (catalogo publico).
Integrante 1 mantiene el CRUD; Integrante 2 consume /api/catalogo desde web y movil."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app.core.database import to_dict
from app.core.deps import get_db, require_roles
from app.models.catalogo import (AssetAR, Coleccion, Color, Prenda, Talla,
                                 Variante)
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal

router = APIRouter()          # /api/prendas  (administracion)
publico = APIRouter()         # /api/catalogo (clientes web y movil)
admin = require_roles("administrador")


class PrendaIn(BaseModel):
    categoria_id: int
    coleccion_id: int | None = None
    nombre: str
    descripcion: str | None = None
    marca: str | None = None
    genero: str | None = None
    precio_venta: float
    costo: float
    imagen_url: str | None = None


class PrendaUpd(BaseModel):
    categoria_id: int | None = None
    coleccion_id: int | None = None
    nombre: str | None = None
    descripcion: str | None = None
    marca: str | None = None
    genero: str | None = None
    precio_venta: float | None = None
    costo: float | None = None
    imagen_url: str | None = None
    activo: bool | None = None


class VarianteIn(BaseModel):
    talla_id: int
    color_id: int
    imagen_url: str | None = None


class AssetIn(BaseModel):
    tipo: str = "png_overlay"
    url_recurso: str
    escala: float = 1


@router.get("", summary="Listar prendas (admin)")
def listar(db=Depends(get_db), _=Depends(admin)):
    return [to_dict(p) for p in db.query(Prenda).all()]


@router.post("", status_code=201, summary="Crear prenda")
def crear(datos: PrendaIn, db=Depends(get_db), _=Depends(admin)):
    p = Prenda(**datos.model_dump())
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Categoria o coleccion inexistente")
    db.refresh(p)
    return to_dict(p)


@router.put("/{id}", summary="Editar prenda")
def editar(id: int, datos: PrendaUpd, db=Depends(get_db), _=Depends(admin)):
    p = db.get(Prenda, id)
    if p is None:
        raise HTTPException(404, "Prenda no encontrada")
    for k, v in datos.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return to_dict(p)


@router.post("/{id}/variantes", status_code=201, summary="Crear variante talla-color")
def crear_variante(id: int, datos: VarianteIn, db=Depends(get_db), _=Depends(admin)):
    if db.get(Prenda, id) is None:
        raise HTTPException(404, "Prenda no encontrada")
    sku = f"P{id}-T{datos.talla_id}-C{datos.color_id}"
    v = Variante(prenda_id=id, sku=sku, **datos.model_dump())
    db.add(v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "La combinacion talla-color ya existe o la talla/color no existe")
    db.refresh(v)
    return to_dict(v)


@router.get("/{id}/variantes", summary="Variantes de una prenda")
def variantes(id: int, db=Depends(get_db), _=Depends(admin)):
    filas = db.query(Variante).filter(Variante.prenda_id == id).all()
    # El panel necesita saber si la variante ya tiene cargado su recurso del
    # probador (CU24); se agrega al listado para no pedir un GET por variante.
    salida = []
    for v in filas:
        assets = db.query(AssetAR).filter(AssetAR.variante_id == v.id).count()
        salida.append({**to_dict(v), "assets_ar": assets, "tiene_asset_ar": assets > 0})
    return salida


@router.post("/variantes/{variante_id}/asset-ar", status_code=201,
             summary="Registrar recurso del probador (PNG fondo transparente)")
def crear_asset(variante_id: int, datos: AssetIn, db=Depends(get_db), _=Depends(admin)):
    if db.get(Variante, variante_id) is None:
        raise HTTPException(404, "Variante no encontrada")
    a = AssetAR(variante_id=variante_id, **datos.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return to_dict(a)


# ------------------------- catalogo publico (sin token) -------------------------
@publico.get("/catalogo", summary="CU16/CU22: catalogo con filtros y disponibilidad")
def catalogo(q: str | None = None, categoria_id: int | None = None,
             temporada_id: int | None = None, coleccion_id: int | None = None,
             talla_id: int | None = None, color_id: int | None = None,
             db=Depends(get_db)):
    consulta = db.query(Prenda).filter(Prenda.activo == True)  # noqa: E712
    if q:
        consulta = consulta.filter(Prenda.nombre.ilike(f"%{q}%"))
    if categoria_id:
        consulta = consulta.filter(Prenda.categoria_id == categoria_id)
    if coleccion_id:
        consulta = consulta.filter(Prenda.coleccion_id == coleccion_id)
    if temporada_id:
        consulta = consulta.join(Coleccion, Prenda.coleccion_id == Coleccion.id)\
                           .filter(Coleccion.temporada_id == temporada_id)

    resultado = []
    for p in consulta.all():
        vq = db.query(Variante).filter(Variante.prenda_id == p.id,
                                       Variante.activo == True)  # noqa: E712
        if talla_id:
            vq = vq.filter(Variante.talla_id == talla_id)
        if color_id:
            vq = vq.filter(Variante.color_id == color_id)
        variantes = []
        for v in vq.all():
            filas = (db.query(Inventario, Sucursal)
                     .join(Sucursal, Inventario.sucursal_id == Sucursal.id)
                     .filter(Inventario.variante_id == v.id).all())
            talla = db.get(Talla, v.talla_id)
            color = db.get(Color, v.color_id)
            variantes.append({
                "id": v.id, "sku": v.sku,
                "talla": talla.nombre if talla else None,
                "color": color.nombre if color else None,
                "imagen_url": v.imagen_url,
                "disponibilidad": [
                    {"sucursal_id": s.id, "sucursal": s.nombre,
                     "disponible": inv.cantidad - inv.cantidad_reservada}
                    for inv, s in filas
                ],
            })
        if (talla_id or color_id) and not variantes:
            continue
        resultado.append({
            "id": p.id, "nombre": p.nombre, "marca": p.marca,
            "precio_venta": float(p.precio_venta), "imagen_url": p.imagen_url,
            "categoria_id": p.categoria_id, "coleccion_id": p.coleccion_id,
            "variantes": variantes,
        })
    return resultado
