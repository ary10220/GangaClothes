from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, require_roles
from . import schemas, service


router = APIRouter(prefix="/usuarios", tags=["CU-03 Usuarios y Roles"])


@router.get("", response_model=list[schemas.UsuarioOut])
def listar(
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """CU-03: Lista todos los usuarios pertenecientes al tenant del usuario autenticado."""
    return service.listar(db, scope.tenant_id)


@router.post("", response_model=schemas.UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear(
    body: schemas.UsuarioIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """CU-03: Crea un nuevo usuario en el tenant.
    - Valida que no se exceda el limite de usuarios del plan contratado (409).
    - Valida que no exista otro usuario con el mismo email en este tenant (409).
    """
    return service.crear(db, scope.tenant_id, body)


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obtener(
    usuario_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.obtener(db, scope.tenant_id, usuario_id)


@router.patch("/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_patch(
    usuario_id: int,
    body: schemas.UsuarioUpdateIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return service.actualizar(db, scope.tenant_id, usuario_id, body)


@router.put("/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_put(
    usuario_id: int,
    body: schemas.UsuarioUpdateIn,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Soporte para PUT desde frontend Angular."""
    return service.actualizar(db, scope.tenant_id, usuario_id, body)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    usuario_id: int,
    scope: TenantScope = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    service.eliminar(db, scope.tenant_id, usuario_id, current_user_id=scope.user_id)
    return None
