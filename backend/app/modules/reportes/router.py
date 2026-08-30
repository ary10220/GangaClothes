"""Modulo pendiente de implementar. CU19 Reportes, dashboard y margen promedio por prenda"""
from fastapi import APIRouter

router = APIRouter()

PLAN = {
    "modulo": "reportes",
    "estado": "pendiente",
    "iteracion": 3,
    "responsable": "Integrante 1",
    "casos_de_uso": "CU19 Reportes, dashboard y margen promedio por prenda",
}


@router.get("", summary="[PENDIENTE] CU19 Reportes, dashboard y margen promedio por prenda")
def plan():
    return PLAN
