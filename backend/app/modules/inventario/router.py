"""Modulo pendiente de implementar. CU10 Compra a proveedor, CU11 Stock min/max y alertas, CU12 Movimientos"""
from fastapi import APIRouter

router = APIRouter()

PLAN = {
    "modulo": "inventario",
    "estado": "pendiente",
    "iteracion": 2,
    "responsable": "Integrante 1",
    "casos_de_uso": "CU10 Compra a proveedor, CU11 Stock min/max y alertas, CU12 Movimientos",
}


@router.get("", summary="[PENDIENTE] CU10 Compra a proveedor, CU11 Stock min/max y alertas, CU12 Movimientos")
def plan():
    return PLAN
