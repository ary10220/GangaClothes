"""CU15 cobro y comprobante en caja; CU17 pago en linea por pasarela.

Los mismos endpoints los consumen la web y la app movil. El flujo del QR son
tres llamadas porque el cobro ocurre fuera del sistema:

    POST /api/pagos/qr           genera el QR y lo deja como pago pendiente
    GET  /api/pagos/qr/{qr_id}   pregunta al banco; si se pago, cierra la venta
    POST /api/pagos/qr/simular   solo con BCP_MODO=simulado, fuerza el desenlace
"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, permisos_de
from app.modules.pagos import service
from app.modules.pagos.pasarelas import qr_bcp
from app.modules.pagos.schemas import PagoIn, QrIn, QrSimularIn

router = APIRouter()


def _bitacora_rechazo(db, usuario, peticion, resultado, como: str) -> None:
    pago, venta = resultado["pago"], resultado["venta"]
    registrar(db, modulo="PAGOS", accion="CREAR", usuario=usuario, peticion=peticion, nivel="ERROR",
              entidad="pago", entidad_id=pago["id"],
              detalle=f"{como} rechazo el pago de la venta #{venta['id']} por Bs {pago['monto']:.2f} "
                      f"({pago['referencia_externa']}); la venta vuelve al carrito")


def _bitacora_cobro(db, usuario, peticion, resultado, como: str) -> None:
    pago, venta = resultado["pago"], resultado["venta"]
    unidades = sum(m["cantidad"] for m in resultado.get("movimientos", []))
    registrar(db, modulo="PAGOS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="pago", entidad_id=pago["id"],
              detalle=f"Cobro de Bs {venta['total']:.2f} por {como} en la venta #{venta['id']}: "
                      f"comprobante {resultado['nro_comprobante']}, {unidades} unidades descontadas")


@router.get("/metodos", summary="Metodos de pago disponibles y estado de cada pasarela")
def metodos(canal: str = Query("web", pattern="^(web|movil|caja)$")):
    return service.metodos_disponibles(canal)


@router.post("", status_code=201, summary="CU15/CU17: registrar un pago; si cubre el total, cierra la venta")
def pagar(datos: PagoIn, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    # El personal cobra en caja con permiso; el cliente paga lo suyo por la pasarela.
    personal = "pagos:crear" in permisos_de(db, usuario.id)
    resultado = service.pagar(db, usuario, datos, personal)
    como = resultado["pago"]["etiqueta"]

    if not resultado["aprobado"]:
        _bitacora_rechazo(db, usuario, peticion, resultado, como)
        # 402: la peticion es valida pero el cobro no se concreto.
        return JSONResponse(status_code=402, content=resultado)

    _bitacora_cobro(db, usuario, peticion, resultado, como)
    return resultado


# --------------------------------------------------------------------------- QR
@router.post("/qr", status_code=201, summary="CU17: generar el QR de cobro de una venta en linea")
def generar_qr(datos: QrIn, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    resultado = service.crear_qr(db, usuario, datos.venta_id)
    registrar(db, modulo="PAGOS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="pago", entidad_id=resultado["pago_id"],
              detalle=f"QR {resultado['qr_id']} generado por Bs {resultado['monto']:.2f} para la "
                      f"venta #{datos.venta_id}; vence {resultado['expira']} "
                      f"({'simulador' if resultado['simulado'] else qr_bcp.modo()})")
    return resultado


@router.get("/qr/{qr_id}", summary="CU17: consultar al banco como quedo el QR y cerrar la venta si se pago")
def consultar_qr(qr_id: str, venta_id: int, peticion: Request,
                 db=Depends(get_db), usuario=Depends(get_current_user)):
    personal = "pagos:ver" in permisos_de(db, usuario.id)
    resultado = service.consultar_qr(db, usuario, venta_id, qr_id, personal)

    if resultado.get("nro_comprobante") and resultado.get("movimientos") is not None:
        _bitacora_cobro(db, usuario, peticion, resultado, "QR (BCP)")
    elif resultado.get("pago") and resultado["pago"]["estado"] == "fallido":
        _bitacora_rechazo(db, usuario, peticion, resultado, "El QR del BCP")

    if resultado.get("rechazado"):
        return JSONResponse(status_code=402, content=resultado)
    return resultado


@router.post("/qr/simular", summary="Solo con BCP_MODO=simulado: forzar el desenlace de un QR")
def simular_qr(datos: QrSimularIn, peticion: Request,
               db=Depends(get_db), usuario=Depends(get_current_user)):
    personal = "pagos:ver" in permisos_de(db, usuario.id)
    resultado = service.simular_qr(db, usuario, datos.venta_id, datos.qr_id, datos.estado, personal)

    if resultado.get("nro_comprobante") and resultado.get("movimientos") is not None:
        _bitacora_cobro(db, usuario, peticion, resultado, "QR (simulador BCP)")
    elif resultado.get("pago") and resultado["pago"]["estado"] == "fallido":
        _bitacora_rechazo(db, usuario, peticion, resultado, "El QR del BCP (simulador)")

    if resultado.get("rechazado"):
        return JSONResponse(status_code=402, content=resultado)
    return resultado


@router.get("", summary="Pagos de una venta")
def listar(venta_id: int | None = None, db=Depends(get_db), usuario=Depends(get_current_user)):
    personal = "pagos:ver" in permisos_de(db, usuario.id)
    return service.listar(db, usuario, venta_id, personal)
