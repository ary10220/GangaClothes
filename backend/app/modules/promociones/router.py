"""CU18 Gestionar promociones (administrador).

El router valida permisos y deja la bitacora; las reglas (vigencia, mayor
descuento, solapamientos) viven en service.py.
"""
from fastapi import APIRouter, Depends, Request

from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.modules.promociones import service
from app.modules.promociones.schemas import PromocionIn, PromocionUpd

router = APIRouter()

ver = require_permiso("promociones:ver")
crear_p = require_permiso("promociones:crear")
editar_p = require_permiso("promociones:editar")
eliminar_p = require_permiso("promociones:eliminar")


def _resumen(p: dict) -> str:
    return (f"'{p['nombre']}' ({p['etiqueta']}, del {p['fecha_inicio']} al {p['fecha_fin']}, "
            f"{len(p['prenda_ids'])} prendas)")


@router.get("", summary="CU18: promociones con su estado, prendas y solapamientos")
def listar(db=Depends(get_db), _=Depends(ver)):
    return service.listar(db)


@router.get("/{id}", summary="CU18: una promocion con sus prendas")
def obtener(id: int, db=Depends(get_db), _=Depends(ver)):
    return service.obtener(db, id)


@router.post("", status_code=201, summary="CU18: crear promocion y asociarle prendas")
def crear(datos: PromocionIn, peticion: Request, db=Depends(get_db), usuario=Depends(crear_p)):
    promo = service.crear(db, datos)
    registrar(db, modulo="PROMOCIONES", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="promocion", entidad_id=promo["id"],
              nivel="ALERTA" if promo["solapamientos"] else "INFO",
              detalle=f"Alta de promocion {_resumen(promo)}"
                      + (". " + promo["advertencia"] if promo["advertencia"] else ""))
    return promo


@router.put("/{id}", summary="CU18: editar promocion, sus fechas o sus prendas")
def editar(id: int, datos: PromocionUpd, peticion: Request, db=Depends(get_db),
           usuario=Depends(editar_p)):
    promo = service.editar(db, id, datos)
    cambios = datos.model_dump(exclude_unset=True)
    if list(cambios) == ["activo"]:
        detalle = f"{'Reactivacion' if cambios['activo'] else 'Desactivacion'} de promocion '{promo['nombre']}'"
    else:
        detalle = f"Cambios en promocion {_resumen(promo)}: {', '.join(cambios) or 'sin cambios'}"
    registrar(db, modulo="PROMOCIONES", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="promocion", entidad_id=id,
              nivel="ALERTA" if promo["solapamientos"] else "INFO",
              detalle=detalle + (". " + promo["advertencia"] if promo["advertencia"] else ""))
    return promo


@router.delete("/{id}", summary="CU18: eliminar promocion (si ya dio descuentos, se desactiva)")
def eliminar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(eliminar_p)):
    nombre, eliminada = service.eliminar(db, id)
    if eliminada:
        registrar(db, modulo="PROMOCIONES", accion="ELIMINAR", usuario=usuario, peticion=peticion,
                  entidad="promocion", entidad_id=id, nivel="ALERTA",
                  detalle=f"Baja de promocion '{nombre}'")
        return {"detail": f"Promocion '{nombre}' eliminada", "eliminada": True}
    registrar(db, modulo="PROMOCIONES", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="promocion", entidad_id=id, nivel="ALERTA",
              detalle=f"Promocion '{nombre}' ya dio descuentos en ventas: se desactivo en vez de borrarse")
    return {"detail": f"'{nombre}' ya se uso en ventas: se desactivo en lugar de eliminarse",
            "eliminada": False}
