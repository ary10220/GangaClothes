"""CU19 Reportes y dashboard.

Todas las rutas piden `reportes:ver`. Los tres reportes aceptan `formato=csv`
para descargarlos y abrirlos en Excel.
"""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.modules.reportes import service

router = APIRouter()
ver = require_permiso("reportes:ver")

Formato = Literal["json", "csv"]


def _descarga(contenido: bytes, nombre: str) -> Response:
    return Response(content=contenido, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def _exportado(db, usuario, peticion, reporte: str, r: dict) -> None:
    p = r["periodo"]
    registrar(db, modulo="REPORTES", accion="EXPORTAR", usuario=usuario, peticion=peticion,
              entidad="reporte", detalle=f"Exporto el reporte de {reporte} del {p['desde']} al {p['hasta']} a CSV")


@router.get("/dashboard", summary="CU19: indicadores principales y series para los graficos")
def dashboard(desde: date | None = None, hasta: date | None = None, sucursal_id: int | None = None,
              db=Depends(get_db), _=Depends(ver)):
    return service.dashboard(db, desde, hasta, sucursal_id)


@router.get("/ventas", summary="CU19: ventas por sucursal, canal y periodo")
def ventas(peticion: Request, desde: date | None = None, hasta: date | None = None,
           sucursal_id: int | None = None, canal: str | None = None,
           agrupar: str = "dia", formato: Formato = "json",
           db=Depends(get_db), usuario=Depends(ver)):
    r = service.ventas(db, desde, hasta, sucursal_id, canal, agrupar)
    if formato == "csv":
        _exportado(db, usuario, peticion, "ventas", r)
        return _descarga(service.csv_ventas(r), f"ventas_{r['periodo']['desde']}_{r['periodo']['hasta']}.csv")
    return r


@router.get("/inventario", summary="CU19: stock valorizado por sucursal y movimientos del periodo")
def inventario(peticion: Request, desde: date | None = None, hasta: date | None = None,
               sucursal_id: int | None = None, formato: Formato = "json",
               db=Depends(get_db), usuario=Depends(ver)):
    r = service.inventario(db, desde, hasta, sucursal_id)
    if formato == "csv":
        _exportado(db, usuario, peticion, "inventario y movimientos", r)
        return _descarga(service.csv_inventario(r),
                         f"inventario_{r['periodo']['desde']}_{r['periodo']['hasta']}.csv")
    return r


@router.get("/margen", summary="CU19: ganancia promedio por prenda (precio_venta - costo)")
def margen(peticion: Request, desde: date | None = None, hasta: date | None = None,
           sucursal_id: int | None = None, formato: Formato = "json",
           db=Depends(get_db), usuario=Depends(ver)):
    r = service.margen(db, desde, hasta, sucursal_id)
    if formato == "csv":
        _exportado(db, usuario, peticion, "ganancia por prenda", r)
        return _descarga(service.csv_margen(r),
                         f"ganancia_por_prenda_{r['periodo']['desde']}_{r['periodo']['hasta']}.csv")
    return r
