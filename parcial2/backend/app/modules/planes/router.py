from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, get_scope
from ...models import Plan
from ..suscripciones.schemas import PlanOut


router = APIRouter(prefix="/planes", tags=["Planes"])


@router.get("", response_model=list[PlanOut])
def listar_planes(
    _: TenantScope = Depends(get_scope),
    db: Session = Depends(get_db),
):
    """Lista los planes activos del catalogo. Cualquier usuario autenticado puede verlos."""
    return db.query(Plan).filter(Plan.activo.is_(True)).order_by(Plan.precio_mensual).all()
