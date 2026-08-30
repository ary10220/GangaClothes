"""Modulo pendiente de implementar. CU13 Atender reservas, CU25 Reservar, CU26 Consultar/Cancelar"""
from fastapi import APIRouter

router = APIRouter()

PLAN = {
    "modulo": "reservas",
    "estado": "pendiente",
    "iteracion": 2,
    "responsable": "Integrante 1 (API) + Integrante 2 (app)",
    "casos_de_uso": "CU13 Atender reservas, CU25 Reservar, CU26 Consultar/Cancelar",
}


@router.get("", summary="[PENDIENTE] CU13 Atender reservas, CU25 Reservar, CU26 Consultar/Cancelar")
def plan():
    return PLAN
