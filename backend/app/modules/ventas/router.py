"""Modulo pendiente de implementar. CU14 Venta presencial, CU17/CU27 Carrito y compra digital"""
from fastapi import APIRouter

router = APIRouter()

PLAN = {
    "modulo": "ventas",
    "estado": "pendiente",
    "iteracion": 2,
    "responsable": "Integrante 1",
    "casos_de_uso": "CU14 Venta presencial, CU17/CU27 Carrito y compra digital",
}


@router.get("", summary="[PENDIENTE] CU14 Venta presencial, CU17/CU27 Carrito y compra digital")
def plan():
    return PLAN
