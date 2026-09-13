"""CU7 (admin de prendas/variantes) y CU16/CU22 (catalogo publico).
Integrante 1 mantiene el CRUD; Integrante 2 consume /api/catalogo desde web y movil.

Las reglas (stock inicial, publicacion, catalogo) viven en service.py.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.core.auditoria import registrar
from app.core.database import to_dict
from app.core.deps import get_db, permisos_de, require_permiso
from app.models.catalogo import AssetAR, Prenda, Variante
from app.models.sucursales import Sucursal
from app.modules.prendas import service

router = APIRouter()          # /api/prendas  (administracion)
publico = APIRouter()         # /api/catalogo (clientes web y movil)
ver = require_permiso("prendas:ver")
crear_p = require_permiso("prendas:crear")
editar_p = require_permiso("prendas:editar")
# Cargar stock es una operacion de inventario (CU11), ademas de prendas.
crear_stock = require_permiso("inventario:crear")


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
    """`publicado` no se cambia aqui: tiene sus propias rutas con la regla de stock."""

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


class StockInicialIn(BaseModel):
    sucursal_id: int
    cantidad: int = Field(ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    stock_maximo: int = Field(default=0, ge=0)


class VarianteIn(BaseModel):
    talla_id: int
    color_id: int
    imagen_url: str | None = None
    # Opcional: sucursales donde la variante nace con unidades.
    stock_inicial: list[StockInicialIn] = []


class GenerarVariantesIn(BaseModel):
    talla_ids: list[int] = Field(min_length=1)
    color_ids: list[int] = Field(min_length=1)
    imagen_url: str | None = None
    stock_inicial: list[StockInicialIn] = []


class StockVarianteIn(BaseModel):
    sucursales: list[StockInicialIn] = Field(min_length=1)


class PublicarIn(BaseModel):
    # Sin stock la publicacion se rechaza con 409 salvo que se confirme.
    confirmar_sin_stock: bool = False


class AssetIn(BaseModel):
    tipo: str = "png_overlay"
    url_recurso: str
    escala: float = 1


def _texto_stock(db, lineas) -> str:
    partes = []
    for l in lineas:
        sucursal = db.get(Sucursal, l.sucursal_id)
        partes.append(f"{sucursal.nombre if sucursal else l.sucursal_id} {l.cantidad}")
    return ", ".join(partes)


def _exigir_stock(db, usuario, lineas) -> None:
    if lineas and "inventario:crear" not in permisos_de(db, usuario.id):
        raise HTTPException(403, "Tu rol no tiene el permiso necesario para cargar stock (inventario:crear)")


# ------------------------------------------------------------------ prendas
@router.get("", summary="Listar prendas con su estado de publicacion y stock resumido (admin)")
def listar(db=Depends(get_db), _=Depends(ver)):
    return service.listar(db)


@router.get("/catalogo-interno",
            summary="Prendas activas, publicadas o no, con variantes y stock por sucursal (caja y compras)")
def catalogo_interno(sucursal_id: int | None = None, db=Depends(get_db), _=Depends(ver)):
    return service.armar_catalogo(db, solo_publicadas=False, sucursal_id=sucursal_id)


@router.post("", status_code=201, summary="Crear prenda (nace sin publicar)")
def crear(datos: PrendaIn, peticion: Request, db=Depends(get_db), usuario=Depends(crear_p)):
    p = Prenda(**datos.model_dump(), publicado=False)
    db.add(p)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Categoria o coleccion inexistente")
    db.refresh(p)
    registrar(db, modulo="PRENDAS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="prenda", entidad_id=p.id, detalle=f"Alta de prenda '{p.nombre}' (sin publicar)")
    return service.prenda_salida(db, p)


@router.put("/{id}", summary="Editar prenda (archivarla tambien la retira de la tienda)")
def editar(id: int, datos: PrendaUpd, peticion: Request, db=Depends(get_db), usuario=Depends(editar_p)):
    cambios = datos.model_dump(exclude_unset=True)
    estaba_publicada = bool(getattr(db.get(Prenda, id), "publicado", False))
    p = service.editar(db, id, cambios)
    if list(cambios) == ["activo"]:
        detalle = f"{'Reactivacion' if cambios['activo'] else 'Archivado'} de prenda '{p['nombre']}'"
        if cambios["activo"] is False and estaba_publicada:
            detalle += " (se retiro de la tienda en linea)"
    else:
        detalle = f"Cambios en prenda '{p['nombre']}': {', '.join(cambios) or 'sin cambios'}"
    registrar(db, modulo="PRENDAS", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="prenda", entidad_id=id, detalle=detalle)
    return p


@router.post("/{id}/publicar", summary="Publicar la prenda en la tienda en linea (409 si no tiene stock)")
def publicar(id: int, peticion: Request, datos: PublicarIn | None = None,
             db=Depends(get_db), usuario=Depends(editar_p)):
    p, sin_stock = service.publicar(db, id, bool(datos and datos.confirmar_sin_stock))
    registrar(db, modulo="PRENDAS", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="prenda", entidad_id=id, nivel="ALERTA" if sin_stock else "INFO",
              detalle=f"Publicacion de prenda '{p['nombre']}'"
                      + (" sin unidades disponibles (confirmado)" if sin_stock
                         else f" con {p['disponible_total']} unidades disponibles"))
    return p


@router.post("/{id}/despublicar", summary="Retirar la prenda de la tienda en linea")
def despublicar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(editar_p)):
    p = service.despublicar(db, id)
    registrar(db, modulo="PRENDAS", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="prenda", entidad_id=id, detalle=f"Prenda '{p['nombre']}' retirada de la tienda en linea")
    return p


# ---------------------------------------------------------------- variantes
@router.post("/{id}/variantes", status_code=201,
             summary="Crear variante talla-color, opcionalmente con stock inicial por sucursal")
def crear_variante(id: int, datos: VarianteIn, peticion: Request, db=Depends(get_db),
                   usuario=Depends(crear_p)):
    _exigir_stock(db, usuario, datos.stock_inicial)
    v, _ = service.crear_variante(db, id, datos, usuario.id)
    stock = f" con stock inicial: {_texto_stock(db, datos.stock_inicial)}" if datos.stock_inicial else ""
    registrar(db, modulo="PRENDAS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="variante", entidad_id=v["id"], detalle=f"Alta de variante {v['sku']}{stock}")
    return v


@router.post("/{id}/variantes/lote", status_code=201,
             summary="Generar las variantes talla x color que falten, con el mismo stock inicial")
def generar_variantes(id: int, datos: GenerarVariantesIn, peticion: Request, db=Depends(get_db),
                      usuario=Depends(crear_p)):
    _exigir_stock(db, usuario, datos.stock_inicial)
    resultado = service.generar_variantes(db, id, datos, usuario.id)
    skus = ", ".join(v["sku"] for v in resultado["creadas"])
    stock = f"; stock inicial por variante: {_texto_stock(db, datos.stock_inicial)}" if datos.stock_inicial else ""
    registrar(db, modulo="PRENDAS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="prenda", entidad_id=id,
              detalle=f"Alta de {len(resultado['creadas'])} variantes de '{resultado['prenda']['nombre']}': {skus}{stock}")
    return resultado


@router.get("/{id}/variantes", summary="Variantes de una prenda con su stock por sucursal")
def variantes(id: int, db=Depends(get_db), _=Depends(ver)):
    return service.variantes_de(db, id)


@router.post("/variantes/{variante_id}/stock-inicial", status_code=201,
             summary="CU11: cargar el stock inicial de una variante en sucursales donde aun no tiene")
def stock_inicial(variante_id: int, datos: StockVarianteIn, peticion: Request, db=Depends(get_db),
                  usuario=Depends(crear_stock)):
    v = service.cargar_stock_inicial(db, variante_id, datos.sucursales, usuario.id)
    registrar(db, modulo="INVENTARIO", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="variante", entidad_id=variante_id,
              detalle=f"Stock inicial de {v['sku']}: {_texto_stock(db, datos.sucursales)}")
    return v


@router.post("/variantes/{variante_id}/asset-ar", status_code=201,
             summary="Registrar recurso del probador (PNG fondo transparente)")
def crear_asset(variante_id: int, datos: AssetIn, peticion: Request, db=Depends(get_db),
                usuario=Depends(editar_p)):
    variante = db.get(Variante, variante_id)
    if variante is None:
        raise HTTPException(404, "Variante no encontrada")
    a = AssetAR(variante_id=variante_id, **datos.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    registrar(db, modulo="PRENDAS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="asset_ar", entidad_id=a.id,
              detalle=f"Recurso {a.tipo} para la variante {variante.sku}")
    return to_dict(a)


# ------------------------- catalogo publico (sin token) -------------------------
@publico.get("/catalogo", summary="CU16/CU22: prendas publicadas con filtros y disponibilidad")
def catalogo(q: str | None = None, categoria_id: int | None = None,
             temporada_id: int | None = None, coleccion_id: int | None = None,
             talla_id: int | None = None, color_id: int | None = None,
             sucursal_id: int | None = None, db=Depends(get_db)):
    """Sin sucursal: todo lo publicado con su disponibilidad en todas las sucursales.
    Con sucursal: solo lo que tiene unidades disponibles en esa sucursal."""
    return service.armar_catalogo(
        db, solo_publicadas=True, q=q, categoria_id=categoria_id, temporada_id=temporada_id,
        coleccion_id=coleccion_id, talla_id=talla_id, color_id=color_id, sucursal_id=sucursal_id,
    )
