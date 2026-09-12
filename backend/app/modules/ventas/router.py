"""CU17 carrito y compra digital (cliente) y CU14 venta presencial (cajero).

El carrito se valida por identidad: el cliente sale del token. La venta en caja
y el listado van por permiso. Ninguna ruta de este modulo descuenta inventario.
"""
from fastapi import APIRouter, Depends, Request, Response

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, permisos_de, require_permiso
from app.modules.ventas import service
from app.modules.ventas.schemas import CarritoIn, ItemIn, ItemUpd, VentaPresencialIn

router = APIRouter()

ver = require_permiso("ventas:ver")
crear = require_permiso("ventas:crear")


# ---------------------------------------------------------- CU17 carrito
@router.post("/carrito", summary="CU17: abrir el carrito (o devolver el que ya existe)")
def abrir_carrito(response: Response, datos: CarritoIn | None = None,
                  db=Depends(get_db), usuario=Depends(get_current_user)):
    carrito, creado = service.abrir_carrito(db, usuario, datos.sucursal_id if datos else None)
    response.status_code = 201 if creado else 200
    return carrito


@router.get("/carrito", summary="CU17: carrito con detalle, stock y totales recalculados")
def ver_carrito(db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.ver_carrito(db, usuario)


@router.post("/carrito/items", status_code=201, summary="CU17: agregar una prenda al carrito")
def agregar_item(datos: ItemIn, db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.agregar_item(db, usuario, datos)


@router.put("/carrito/items/{id}", summary="CU17: cambiar la cantidad de un item")
def cambiar_item(id: int, datos: ItemUpd, db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.cambiar_item(db, usuario, id, datos.cantidad)


@router.delete("/carrito/items/{id}", summary="CU17: quitar un item del carrito")
def quitar_item(id: int, db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.quitar_item(db, usuario, id)


@router.post("/carrito/confirmar", summary="CU17: cerrar el carrito, queda pendiente de pago")
def confirmar(peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    venta = service.confirmar(db, usuario)
    registrar(db, modulo="VENTAS", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="venta", entidad_id=venta["id"],
              detalle=f"Carrito #{venta['id']} confirmado por Bs {venta['total']:.2f} "
                      f"({venta['unidades']} unidades), pendiente de pago")
    return venta


# -------------------------------------------------------- CU14 presencial
@router.post("/presencial", status_code=201, summary="CU14: venta en caja, opcionalmente desde una reserva")
def crear_presencial(datos: VentaPresencialIn, peticion: Request,
                     db=Depends(get_db), usuario=Depends(crear)):
    venta = service.crear_presencial(db, usuario, datos)
    origen = f" desde la reserva #{venta['reserva_id']}" if venta["reserva_id"] else ""
    registrar(db, modulo="VENTAS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="venta", entidad_id=venta["id"],
              detalle=f"Venta en caja #{venta['id']}{origen} por Bs {venta['total']:.2f}, pendiente de cobro")
    return venta


@router.get("", summary="Ventas por sucursal, canal y estado")
def listar(sucursal_id: int | None = None, canal: str | None = None, estado: str | None = None,
           db=Depends(get_db), _=Depends(ver)):
    return service.listar(db, sucursal_id, canal, estado)


# ------------------------------------------------------ CU15 comprobante
@router.get("/{id}/comprobante", summary="CU15: datos del ticket de una venta pagada")
def comprobante(id: int, db=Depends(get_db), usuario=Depends(get_current_user)):
    # El personal ve cualquiera; un cliente, solo los de sus compras.
    personal = "ventas:ver" in permisos_de(db, usuario.id)
    return service.comprobante(db, usuario, id, personal)
