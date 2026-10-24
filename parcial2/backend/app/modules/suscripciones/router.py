from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles, require_tenant
from . import schemas, service


router = APIRouter(prefix="/suscripciones", tags=["CU-05/07 Suscripciones"])


@router.post("/contratar", response_model=schemas.SuscripcionOut)
def contratar(
    body: schemas.ContratarPlanIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """CU-05: el administrador del tenant contrata un plan."""
    sub = service.contratar_plan(db, scope.tenant_id, body)
    db.refresh(sub)
    return schemas.SuscripcionOut(
        id=sub.id,
        plan=schemas.PlanOut.model_validate(sub.plan),
        fecha_inicio=sub.fecha_inicio,
        fecha_fin=sub.fecha_fin,
        estado=sub.estado,
    )


@router.get("/estado", response_model=schemas.EstadoSuscripcionOut)
def consultar_estado(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """CU-07: estado del plan vigente + consumo real por cada limite."""
    return service.consumo(db, scope.tenant_id)
