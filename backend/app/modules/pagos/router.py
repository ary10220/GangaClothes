"""Modulo pendiente de implementar. CU15 Pago en caja y comprobante, CU17/CU27 Stripe modo prueba"""
from fastapi import APIRouter

router = APIRouter()

PLAN = {
    "modulo": "pagos",
    "estado": "pendiente",
    "iteracion": 2,
    "responsable": "Integrante 1",
    "casos_de_uso": "CU15 Pago en caja y comprobante, CU17/CU27 Stripe modo prueba",
}


@router.get("", summary="[PENDIENTE] CU15 Pago en caja y comprobante, CU17/CU27 Stripe modo prueba")
def plan():
    return PLAN
