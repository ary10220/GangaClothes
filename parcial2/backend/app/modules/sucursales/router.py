from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles, require_tenant
from . import schemas, service


router = APIRouter(prefix="/sucursales", tags=["CU-04 Sucursales"])


@router.get("", response_model=list[schemas.SucursalOut])
def listar(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.listar(db, scope.tenant_id)


@router.post("", response_model=schemas.SucursalOut, status_code=status.HTTP_201_CREATED)
def crear(
    body: schemas.SucursalIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """CU-04 + acoplado a CU-05/07: el alta rechaza con 409 si se supera el limite del plan."""
    return service.crear(db, scope.tenant_id, body)


@router.get("/{sucursal_id}", response_model=schemas.SucursalOut)
def obtener(
    sucursal_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener(db, scope.tenant_id, sucursal_id)


@router.patch("/{sucursal_id}", response_model=schemas.SucursalOut)
def actualizar(
    sucursal_id: int,
    body: schemas.SucursalUpdateIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.actualizar(db, scope.tenant_id, sucursal_id, body)


@router.delete("/{sucursal_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    sucursal_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar(db, scope.tenant_id, sucursal_id)
    return None
