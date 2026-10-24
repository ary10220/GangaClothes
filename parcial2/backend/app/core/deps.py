from __future__ import annotations

from typing import Iterator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import SessionLocal, TenantScope, attach_scope
from .security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _scope_from_token(token: str | None) -> TenantScope:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta token")
    try:
        payload = decode_access_token(token)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))

    kind = payload.get("kind")
    sub = payload.get("sub")
    user_id = int(sub) if sub is not None else None
    if kind == "super":
        return TenantScope(
            user_id=user_id,
            tenant_id=None,
            roles=["superadmin"],
            is_super=True,
        )
    if kind == "tenant":
        tid = payload.get("tenant_id")
        if tid is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de tenant sin tenant_id")
        return TenantScope(
            user_id=user_id,
            tenant_id=int(tid),
            roles=list(payload.get("roles") or []),
            is_super=False,
        )
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token con 'kind' invalido")


def get_scope(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> TenantScope:
    """Decodifica el JWT, deja el scope en la sesion y lo retorna.
    Toda ruta protegida depende de esto, asi el filtro automatico de tenant
    tiene scope garantizado.
    """
    scope = _scope_from_token(token)
    attach_scope(db, scope)
    return scope


def require_super(scope: TenantScope = Depends(get_scope)) -> TenantScope:
    if not scope.is_super:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo superadministrador")
    return scope


def require_tenant(scope: TenantScope = Depends(get_scope)) -> TenantScope:
    if scope.is_super or scope.tenant_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Se requiere scope de tenant")
    return scope


def require_roles(*roles: str):
    def _dep(scope: TenantScope = Depends(require_tenant)) -> TenantScope:
        if not any(r in scope.roles for r in roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requiere rol: {roles}")
        return scope

    return _dep
