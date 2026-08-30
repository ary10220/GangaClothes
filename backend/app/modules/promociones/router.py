"""Modulo pendiente de implementar. CU18 Gestionar promociones"""
from fastapi import APIRouter

router = APIRouter()

PLAN = {
    "modulo": "promociones",
    "estado": "pendiente",
    "iteracion": 3,
    "responsable": "Integrante 1",
    "casos_de_uso": "CU18 Gestionar promociones",
}


@router.get("", summary="[PENDIENTE] CU18 Gestionar promociones")
def plan():
    return PLAN
