from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles, require_tenant
from . import schemas, service


router = APIRouter(prefix="/clientes", tags=["CU-11 Clientes del Tenant"])


@router.get("", response_model=list[schemas.ClienteOut])
def listar_clientes(
    q: str | None = Query(default=None, description="Buscar por nombre, apellido, CI/NIT, teléfono o email"),
    tipo: str | None = Query(default=None, description="Filtrar por tipo (regular, mayorista, vip)"),
    activo: bool | None = Query(default=None, description="Filtrar por estado activo/inactivo"),
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """CU-11: Lista clientes del tenant autenticado con filtros opcionales."""
    return service.listar_clientes(
        db,
        scope.tenant_id,
        q=q,
        tipo=tipo,
        activo=activo,
    )


@router.post("", response_model=schemas.ClienteOut, status_code=status.HTTP_201_CREATED)
def crear_cliente(
    body: schemas.ClienteIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado", "cajero")),
    db: Session = Depends(get_db),
):
    """CU-11: Registra un nuevo cliente para la empresa.
    - Valida unicidad de correo en la empresa (409 si ya existe).
    - Valida unicidad de CI/NIT en la empresa (409 si ya existe).
    """
    return service.crear_cliente(db, scope.tenant_id, body)


@router.get("/{cliente_id}", response_model=schemas.ClienteOut)
def obtener_cliente(
    cliente_id: int,
    scope: TenantScope = Depends(require_tenant),
    db: Session = Depends(get_db),
):
    """CU-11: Detalle de cliente. Devuelve 404 si pertenece a otra empresa."""
    return service.obtener_cliente(db, scope.tenant_id, cliente_id)


@router.patch("/{cliente_id}", response_model=schemas.ClienteOut)
def actualizar_cliente_patch(
    cliente_id: int,
    body: schemas.ClienteUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado", "cajero")),
    db: Session = Depends(get_db),
):
    """CU-11: Actualización parcial de cliente."""
    return service.actualizar_cliente(db, scope.tenant_id, cliente_id, body)


@router.put("/{cliente_id}", response_model=schemas.ClienteOut)
def actualizar_cliente_put(
    cliente_id: int,
    body: schemas.ClienteUpdateIn,
    scope: TenantScope = Depends(require_roles("admin", "encargado", "cajero")),
    db: Session = Depends(get_db),
):
    """CU-11: Actualización de cliente (soporte PUT para formularios web)."""
    return service.actualizar_cliente(db, scope.tenant_id, cliente_id, body)


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cliente(
    cliente_id: int,
    scope: TenantScope = Depends(require_roles("admin", "encargado")),
    db: Session = Depends(get_db),
):
    """CU-11: Elimina un cliente de la empresa."""
    service.eliminar_cliente(db, scope.tenant_id, cliente_id)
    return None
