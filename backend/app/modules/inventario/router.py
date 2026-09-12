"""CU10 compra a proveedor, CU11 stock minimo/maximo y alertas, CU12 movimientos.

Sigue el patron de auth/: el router solo valida permisos y traduce la entrada;
las reglas de stock viven en service.py.
"""
from fastapi import APIRouter, Depends, Request

from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.modules.inventario import service
from app.modules.inventario.schemas import (CompraIn, InventarioIn, LimitesUpd,
                                            MovimientoIn)

router = APIRouter()    # /api/inventario
compras = APIRouter()   # /api/compras

# Por el seed, inventario:ver lo tienen encargado, administrador y cajero;
# crear/editar solo encargado y administrador. Se administra desde la
# pantalla de roles, no se cambia aqui.
ver = require_permiso("inventario:ver")
crear = require_permiso("inventario:crear")
editar = require_permiso("inventario:editar")


# ------------------------------------------------------ CU11: stock y alertas
@router.get("", summary="CU11: stock por sucursal con minimos y maximos")
def listar(sucursal_id: int | None = None, db=Depends(get_db), _=Depends(ver)):
    return service.listar(db, sucursal_id)


@router.get("/alertas", summary="CU11: variantes que llegaron al stock minimo")
def alertas(sucursal_id: int | None = None, db=Depends(get_db), _=Depends(ver)):
    return service.listar(db, sucursal_id, solo_alertas=True)


@router.post("", status_code=201, summary="CU11: abrir el stock de una variante en una sucursal")
def crear_registro(datos: InventarioIn, peticion: Request, db=Depends(get_db), usuario=Depends(crear)):
    fila = service.crear_registro(db, datos)
    registrar(db, modulo="INVENTARIO", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="inventario", entidad_id=fila["id"],
              detalle=f"Alta de stock de {fila['sku']} en {fila['sucursal']} "
                      f"con {fila['cantidad']} unidades")
    return fila


@router.put("/{id}", summary="CU11: actualizar stock minimo y maximo")
def actualizar_limites(id: int, datos: LimitesUpd, peticion: Request,
                       db=Depends(get_db), usuario=Depends(editar)):
    fila = service.actualizar_limites(db, id, datos)
    registrar(db, modulo="INVENTARIO", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="inventario", entidad_id=id,
              detalle=f"Limites de {fila['sku']} en {fila['sucursal']}: "
                      f"minimo {fila['stock_minimo']}, maximo {fila['stock_maximo']}")
    return fila


# -------------------------------------------------------- CU12: movimientos
@router.post("/movimientos", status_code=201, summary="CU12: registrar un movimiento de stock")
def crear_movimiento(datos: MovimientoIn, peticion: Request,
                     db=Depends(get_db), usuario=Depends(editar)):
    resultado = service.registrar_movimiento(db, datos, usuario.id)
    m = resultado["movimiento"]
    registrar(db, modulo="INVENTARIO", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="movimiento_inventario", entidad_id=m["id"],
              nivel="ALERTA" if resultado["inventario"]["bajo_minimo"] else "INFO",
              detalle=f"{m['tipo'].title()} de {m['cantidad']} en {m['sku']} "
                      f"({m['sucursal']}): stock {resultado['stock_anterior']} -> "
                      f"{resultado['stock_actual']}")
    return resultado


@router.get("/movimientos", summary="CU12: historial de movimientos, del mas nuevo al mas viejo")
def listar_movimientos(sucursal_id: int | None = None, variante_id: int | None = None,
                       db=Depends(get_db), _=Depends(ver)):
    return service.listar_movimientos(db, sucursal_id, variante_id)


# ---------------------------------------------------- CU10: compra a proveedor
@compras.post("", status_code=201, summary="CU10: registrar una compra a proveedor")
def crear_compra(datos: CompraIn, peticion: Request, db=Depends(get_db), usuario=Depends(crear)):
    compra = service.crear_compra(db, datos)
    registrar(db, modulo="INVENTARIO", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="compra", entidad_id=compra["id"],
              detalle=f"Compra #{compra['id']} a {compra['proveedor']} por Bs {compra['total']:.2f} "
                      f"({compra['items']} lineas), pendiente de recibir")
    return compra


@compras.get("", summary="CU10: listado de compras")
def listar_compras(sucursal_id: int | None = None, estado: str | None = None,
                   db=Depends(get_db), _=Depends(ver)):
    return service.listar_compras(db, sucursal_id, estado)


@compras.get("/{id}", summary="CU10: compra con su detalle")
def obtener_compra(id: int, db=Depends(get_db), _=Depends(ver)):
    return service.obtener_compra(db, id)


@compras.post("/{id}/recibir", summary="CU10: recibir la compra y sumar el stock")
def recibir_compra(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(editar)):
    resultado = service.recibir_compra(db, id, usuario.id)
    compra = resultado["compra"]
    unidades = sum(m["cantidad"] for m in resultado["movimientos"])
    registrar(db, modulo="INVENTARIO", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="compra", entidad_id=compra["id"],
              detalle=f"Recepcion de la compra #{compra['id']}: {unidades} unidades "
                      f"ingresadas en {compra['sucursal']}")
    return resultado
