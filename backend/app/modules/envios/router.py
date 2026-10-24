"""CU29 delivery: cotizar, pedir el envio (cliente) y despacharlo (sucursal).

Como en reservas, las rutas del cliente NO piden permiso por codigo: con
`envios:ver` un cliente veria los envios de toda la sucursal. Se validan por
identidad (el cliente sale del token) y por dueno. Las de la sucursal si van
por permiso, asi que lo que se saque en «Roles y permisos» desaparece del menu,
de la ruta y de la API a la vez.

Ninguna ruta de este modulo toca el inventario: eso pasa una sola vez, al
cobrarse la venta (modulo `pagos`).
"""
from fastapi import APIRouter, Depends, Request

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, permisos_de, require_permiso
from app.modules.envios import service, tarifa
from app.modules.envios.schemas import AsignarIn, CancelarIn, CotizarIn, EnvioIn

router = APIRouter()

ver = require_permiso("envios:ver")
editar = require_permiso("envios:editar")


def _auditar(db, usuario, peticion, envio_id: int, detalle: str,
             accion: str = "EDITAR", nivel: str = "INFO") -> None:
    registrar(db, modulo="ENVIOS", accion=accion, usuario=usuario, peticion=peticion,
              entidad="envio", entidad_id=envio_id, nivel=nivel, detalle=detalle)


def _destino(envio: dict) -> str:
    """"Av. Banzer 123 (Sucursal Norte)" para los mensajes de la bitacora."""
    sucursal = (envio.get("sucursal") or {}).get("nombre") or "la sucursal"
    return f"{envio['direccion']} ({sucursal})"


# ------------------------------------------------------------------- cliente
@router.get("/tarifa", summary="CU29: la tarifa vigente (base, km, express y envio gratis)")
def tarifa_vigente():
    # Publica a proposito: "envio gratis desde Bs 500" es informacion de venta
    # y la muestra el catalogo, donde todavia no hay sesion.
    return tarifa.parametros()


@router.post("/cotizar", summary="CU29: distancia, costo desglosado y tiempo estimado (no crea nada)")
def cotizar(datos: CotizarIn, db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.cotizar(db, usuario, datos)


@router.post("", status_code=201, summary="CU29: pedir entrega a domicilio para una compra")
def crear(datos: EnvioIn, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    resultado = service.crear(db, usuario, datos)
    envio = resultado["envio"]
    _auditar(db, usuario, peticion, envio["id"], accion="CREAR",
             detalle=f"Envio #{envio['id']} de la compra #{envio['venta']['id']} a "
                     f"{_destino(envio)}: {envio['distancia_km']} km, "
                     f"Bs {envio['costo_envio']:.2f}"
                     + (" (express)" if envio["express"] else ""))
    return resultado


@router.get("/mios", summary="CU29: mis envios con su estado y su linea de tiempo")
def mios(db=Depends(get_db), usuario=Depends(get_current_user)):
    return service.mios(db, usuario)


@router.delete("/{id}", summary="CU29: deshacer el envio y volver a retiro en sucursal (antes de pagar)")
def quitar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    venta = service.quitar(db, usuario, id)
    _auditar(db, usuario, peticion, id,
             detalle=f"Envio #{id} descartado: la compra #{venta['id']} vuelve a retiro en sucursal")
    return venta


# ------------------------------------------------------------------ sucursal
@router.get("", summary="CU29: envios de la sucursal por estado (los pendientes primero)")
def listar(sucursal_id: int | None = None, estado: str | None = None,
           db=Depends(get_db), _=Depends(ver)):
    return service.listar(db, sucursal_id, estado)


@router.get("/{id}", summary="CU29: un envio (el cliente solo los suyos)")
def obtener(id: int, db=Depends(get_db), usuario=Depends(get_current_user)):
    personal = "envios:ver" in permisos_de(db, usuario.id)
    return service.ver(db, usuario, id, personal)


@router.post("/{id}/asignar", summary="CU29: pendiente -> asignado (se le da a un repartidor)")
def asignar(id: int, datos: AsignarIn, peticion: Request, db=Depends(get_db), usuario=Depends(editar)):
    envio = service.asignar(db, id, datos.repartidor)
    _auditar(db, usuario, peticion, id,
             detalle=f"Envio #{id} asignado a {envio['repartidor']} para llevarlo a {_destino(envio)}")
    return envio


@router.post("/{id}/en-camino", summary="CU29: asignado -> en camino (el repartidor salio)")
def en_camino(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(editar)):
    envio = service.en_camino(db, id)
    _auditar(db, usuario, peticion, id,
             detalle=f"Envio #{id} en camino con {envio['repartidor']} hacia {_destino(envio)}")
    return envio


@router.post("/{id}/entregar", summary="CU29: en camino -> entregado")
def entregar(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(editar)):
    envio = service.entregar(db, id)
    cliente = (envio.get("cliente") or {}).get("nombre") or "el cliente"
    _auditar(db, usuario, peticion, id,
             detalle=f"Envio #{id} entregado a {cliente} en {envio['direccion']} "
                     f"(compra {envio['venta']['nro_comprobante'] or '#' + str(envio['venta']['id'])})")
    return envio


@router.post("/{id}/cancelar", summary="CU29: cancelar el envio (la venta cobrada no se revierte)")
def cancelar(id: int, peticion: Request, datos: CancelarIn | None = None,
             db=Depends(get_db), usuario=Depends(editar)):
    envio = service.cancelar(db, id, datos.motivo if datos else None)
    motivo = f": {envio['motivo_cancelacion']}" if envio["motivo_cancelacion"] else ""
    _auditar(db, usuario, peticion, id, nivel="ALERTA",
             detalle=f"Envio #{id} a {_destino(envio)} cancelado{motivo}. "
                     f"La compra #{envio['venta']['id']} sigue cobrada")
    return envio
