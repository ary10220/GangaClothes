from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles, require_tenant
from . import schemas, service


router = APIRouter(prefix="/proveedores", tags=["CU-10 Proveedores"])


@router.get("", response_model=list[schemas.ProveedorOut])
def listar(
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """CU-10: Lista todos los proveedores del tenant autenticado."""
    return service.listar(db, scope.tenant_id)


@router.post("", response_model=schemas.ProveedorOut, status_code=status.HTTP_201_CREATED)
def crear(
    body: schemas.ProveedorIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    """CU-10: Registra un nuevo proveedor en el tenant."""
    return service.crear(db, scope.tenant_id, body)


@router.get("/{proveedor_id}", response_model=schemas.ProveedorOut)
def obtener(
    proveedor_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    return service.obtener(db, scope.tenant_id, proveedor_id)


@router.patch("/{proveedor_id}", response_model=schemas.ProveedorOut)
def actualizar_patch(
    proveedor_id: int,
    body: schemas.ProveedorUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    return service.actualizar(db, scope.tenant_id, proveedor_id, body)


@router.put("/{proveedor_id}", response_model=schemas.ProveedorOut)
def actualizar_put(
    proveedor_id: int,
    body: schemas.ProveedorUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    """Soporte para PUT desde frontend Angular."""
    return service.actualizar(db, scope.tenant_id, proveedor_id, body)


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    proveedor_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar(db, scope.tenant_id, proveedor_id)
    return None
