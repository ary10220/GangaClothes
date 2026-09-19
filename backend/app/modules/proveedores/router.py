"""CU9 Informar productos disponibles.

/api/oferta/mia...  portal del proveedor: permisos `oferta:*` y, ademas, la
                    cuenta tiene que estar enlazada a un proveedor. Siempre
                    trabaja sobre la oferta propia: el proveedor sale del token.
/api/oferta         consulta del personal al armar una compra (inventario:crear).
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.modules.proveedores import service

router = APIRouter()

ver_mia = require_permiso("oferta:ver")
crear_mia = require_permiso("oferta:crear")
editar_mia = require_permiso("oferta:editar")
eliminar_mia = require_permiso("oferta:eliminar")
# Consulta la oferta quien puede armar una compra (encargado y administrador).
consultar = require_permiso("inventario:crear")
# Decir a que prenda del catalogo corresponde un producto es gestion de inventario.
asociar = require_permiso("inventario:editar")


class ProductoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=300)
    categoria_id: int | None = None
    precio_referencial: float = Field(gt=0)
    cantidad_minima: int = Field(default=1, ge=1)
    disponible: bool = True
    temporada_ids: list[int] = []


class CorrespondenciaIn(BaseModel):
    """prenda_id nulo = el producto queda sin correspondencia."""

    prenda_id: int | None = None


class ProductoUpd(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=300)
    categoria_id: int | None = None
    precio_referencial: float | None = Field(default=None, gt=0)
    cantidad_minima: int | None = Field(default=None, ge=1)
    disponible: bool | None = None
    temporada_ids: list[int] | None = None


# ------------------------------------------------------ portal del proveedor
@router.get("/perfil", summary="CU9: datos del proveedor enlazado a la cuenta")
def perfil(db=Depends(get_db), usuario=Depends(ver_mia)):
    return service.perfil(db, usuario)


@router.get("/mia", summary="CU9: mi lista de productos ofrecidos")
def mia(db=Depends(get_db), usuario=Depends(ver_mia)):
    return service.mia(db, usuario)


@router.post("/mia", status_code=201, summary="CU9: registrar un producto en mi oferta")
def crear(datos: ProductoIn, peticion: Request, db=Depends(get_db), usuario=Depends(crear_mia)):
    p = service.crear(db, usuario, datos)
    registrar(db, modulo="OFERTA", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="producto_proveedor", entidad_id=p["id"],
              detalle=f"{p['proveedor']} ofrece '{p['nombre']}' a Bs {p['precio_referencial']:.2f}")
    return p


@router.put("/mia/{id}", summary="CU9: actualizar precio, temporadas o disponibilidad de un producto")
def editar(id: int, datos: ProductoUpd, peticion: Request, db=Depends(get_db),
           usuario=Depends(editar_mia)):
    p = service.editar(db, usuario, id, datos)
    cambios = datos.model_dump(exclude_unset=True)
    registrar(db, modulo="OFERTA", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="producto_proveedor", entidad_id=id,
              detalle=f"{p['proveedor']} actualizo '{p['nombre']}': {', '.join(cambios) or 'sin cambios'}")
    return p


@router.delete("/mia/{id}", summary="CU9: quitar un producto de mi oferta")
def eliminar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(eliminar_mia)):
    nombre, quitado = service.eliminar(db, usuario, id)
    if not quitado:
        registrar(db, modulo="OFERTA", accion="EDITAR", usuario=usuario, peticion=peticion,
                  entidad="producto_proveedor", entidad_id=id, nivel="ALERTA",
                  detalle=f"'{nombre}' ya figura en compras de la tienda: quedo sin disponibilidad en vez de borrarse")
        return {"detail": f"'{nombre}' ya figura en compras de la tienda: quedo sin disponibilidad "
                          "en lugar de borrarse", "quitado": False}
    registrar(db, modulo="OFERTA", accion="ELIMINAR", usuario=usuario, peticion=peticion,
              entidad="producto_proveedor", entidad_id=id, nivel="ALERTA",
              detalle=f"Quito '{nombre}' de su oferta")
    return {"detail": f"'{nombre}' ya no esta en tu oferta", "quitado": True}


# ---------------------------------------------------- consulta del personal
@router.get("", summary="CU9/CU10: oferta de los proveedores, para armar una compra")
def oferta(proveedor_id: int | None = None, temporada_id: int | None = None, q: str | None = None,
           solo_disponibles: bool = True, db=Depends(get_db), _=Depends(consultar)):
    return service.consultar(db, proveedor_id, temporada_id, q, solo_disponibles)


@router.put("/{id}/prenda", summary="CU9/CU10: a que prenda del catalogo corresponde un producto ofrecido")
def asociar_prenda(id: int, datos: CorrespondenciaIn, peticion: Request, db=Depends(get_db),
                   usuario=Depends(asociar)):
    p = service.asociar_prenda(db, id, datos.prenda_id)
    registrar(db, modulo="OFERTA", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="producto_proveedor", entidad_id=id,
              detalle=(f"'{p['nombre']}' de {p['proveedor']} corresponde a la prenda '{p['prenda']}'"
                       if p["prenda_id"] else f"'{p['nombre']}' de {p['proveedor']} quedo sin correspondencia"))
    return p
