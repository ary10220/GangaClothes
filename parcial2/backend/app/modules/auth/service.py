from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...core.security import create_access_token, verify_password
from ...models import SuperAdmin, Tenant, User
from . import schemas


_CREDS_INVALID = "Credenciales invalidas"


def login_tenant(db: Session, data: schemas.LoginIn) -> schemas.TokenOut:
    tenant = db.query(Tenant).filter(Tenant.codigo == data.codigo_tenant).first()
    if not tenant or not tenant.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _CREDS_INVALID)

    user = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.email == data.email)
        .first()
    )
    if not user or not user.activo or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _CREDS_INVALID)

    roles = [user.rol]
    token = create_access_token({
        "kind": "tenant",
        "sub": str(user.id),
        "tenant_id": tenant.id,
        "roles": roles,
    })
    return schemas.TokenOut(
        access_token=token,
        kind="tenant",
        tenant_id=tenant.id,
        tenant_codigo=tenant.codigo,
        user_id=user.id,
        nombre=user.nombre,
        roles=roles,
    )


def login_super(db: Session, data: schemas.SuperLoginIn) -> schemas.TokenOut:
    super_user = db.query(SuperAdmin).filter(SuperAdmin.email == data.email).first()
    if not super_user or not super_user.activo or not verify_password(data.password, super_user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, _CREDS_INVALID)

    token = create_access_token({
        "kind": "super",
        "sub": str(super_user.id),
        "roles": ["superadmin"],
    })
    return schemas.TokenOut(
        access_token=token,
        kind="super",
        user_id=super_user.id,
        nombre=super_user.nombre,
        roles=["superadmin"],
    )
