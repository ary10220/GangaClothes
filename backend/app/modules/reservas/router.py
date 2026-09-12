"""CU23 reservar y CU24 consultar/cancelar (cliente); CU13 atender reservas (sucursal).

Los endpoints del cliente no piden permiso por codigo: con `reservas:ver` un
cliente veria las reservas de toda la sucursal. Se validan por identidad (el
perfil de cliente sale del token) y por dueno. Los de sucursal si van por permiso.
"""
from fastapi import APIRouter, Depends, Request

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, require_permiso
from app.modules.reservas import service
from app.modules.reservas.schemas import ReservaIn

router = APIRouter()

ver = require_permiso("reservas:ver")
editar = require_permiso("reservas:editar")


def _auditar(db, usuario, peticion, reserva_id: int, detalle: str, accion="EDITAR", nivel="INFO"):
    registrar(db, modulo="RESERVAS", accion=accion, usuario=usuario, peticion=peticion,
              entidad="reserva", entidad_id=reserva_id, nivel=nivel, detalle=detalle)


# ---------------------------------------------------------------- cliente
@router.post("", status_code=201, summary="CU23: reservar prendas para probarse en tienda")
def crear(datos: ReservaIn, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    reserva = service.crear(db, usuario, datos)
    _auditar(db, usuario, peticion, reserva["id"], accion="CREAR",
             detalle=f"Reserva #{reserva['id']} en {reserva['sucursal']}: {reserva['unidades']} "
                     f"unidades para el {reserva['fecha_hora_prueba']}")
    return reserva


@router.get("/mias", summary="CU24: mis reservas con su detalle y estado")
def mias(db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.mias(db, usuario)


@router.post("/{id}/cancelar", summary="CU24: cancelar una reserva propia pendiente o preparada")
def cancelar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    reserva, liberadas = service.cancelar(db, usuario, id)
    _auditar(db, usuario, peticion, id,
             detalle=f"Reserva #{id} cancelada por el cliente: {liberadas} unidades liberadas")
    return reserva


# --------------------------------------------------------------- sucursal
@router.get("", summary="CU13: reservas de la sucursal, de la cita mas proxima a la mas lejana")
def listar(sucursal_id: int | None = None, estado: str | None = None,
           db=Depends(get_db), _=Depends(ver)):
    return service.listar(db, sucursal_id, estado)


@router.post("/{id}/preparar", summary="CU13: pendiente -> preparada")
def preparar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(editar)):
    reserva, _ = service.preparar(db, id)
    _auditar(db, usuario, peticion, id, detalle=f"Reserva #{id} preparada para el vestidor")
    return reserva


@router.post("/{id}/atender", summary="CU13: preparada -> atendida (el cliente llego)")
def atender(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(editar)):
    reserva, liberadas = service.atender(db, id)
    _auditar(db, usuario, peticion, id,
             detalle=f"Reserva #{id} atendida: {liberadas} unidades dejan de estar apartadas")
    return reserva


@router.post("/{id}/expirar", summary="CU13: el cliente no vino, se libera el stock")
def expirar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(editar)):
    reserva, liberadas = service.expirar(db, id)
    _auditar(db, usuario, peticion, id, nivel="ALERTA",
             detalle=f"Reserva #{id} expirada: {liberadas} unidades liberadas")
    return reserva
