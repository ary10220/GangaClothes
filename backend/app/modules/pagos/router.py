"""CU15 cobro y comprobante en caja; CU17 pago por pasarela (Stripe simulado)."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, permisos_de
from app.modules.pagos import service
from app.modules.pagos.schemas import PagoIn

router = APIRouter()


@router.post("", status_code=201, summary="CU15/CU17: registrar un pago; si cubre el total, cierra la venta")
def pagar(datos: PagoIn, peticion: Request, db=Depends(get_db), usuario=Depends(get_current_user)):
    # El personal cobra en caja con permiso; el cliente paga lo suyo por la pasarela.
    personal = "pagos:crear" in permisos_de(db, usuario.id)
    resultado = service.pagar(db, usuario, datos, personal)
    pago, venta = resultado["pago"], resultado["venta"]

    if not resultado["aprobado"]:
        registrar(db, modulo="PAGOS", accion="CREAR", usuario=usuario, peticion=peticion, nivel="ERROR",
                  entidad="pago", entidad_id=pago["id"],
                  detalle=f"Pasarela rechazo el pago de la venta #{venta['id']} por Bs {pago['monto']:.2f} "
                          f"({pago['referencia_externa']}); la venta vuelve al carrito")
        # 402: la peticion es valida pero el cobro no se concreto.
        return JSONResponse(status_code=402, content=resultado)

    unidades = sum(m["cantidad"] for m in resultado["movimientos"])
    registrar(db, modulo="PAGOS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="pago", entidad_id=pago["id"],
              detalle=f"Cobro de Bs {venta['total']:.2f} por {pago['metodo']} en la venta #{venta['id']}: "
                      f"comprobante {resultado['nro_comprobante']}, {unidades} unidades descontadas")
    return resultado


@router.get("", summary="Pagos de una venta")
def listar(venta_id: int | None = None, db=Depends(get_db), usuario=Depends(get_current_user)):
    personal = "pagos:ver" in permisos_de(db, usuario.id)
    return service.listar(db, usuario, venta_id, personal)
