from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import TenantScope
from ...core.deps import get_db, get_scope
from ...models import SuperAdmin, Tenant, User
from . import schemas, service


router = APIRouter(prefix="/auth", tags=["CU-02 Autenticacion"])


@router.post("/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, db: Session = Depends(get_db)):
    """CU-02: login de un usuario con contexto de tenant.
    Devuelve JWT con `kind='tenant'`, `tenant_id`, `sub` y `roles`.
    """
    return service.login_tenant(db, body)


@router.post("/super/login", response_model=schemas.TokenOut)
def super_login(body: schemas.SuperLoginIn, db: Session = Depends(get_db)):
    """Login del superadministrador de plataforma (sin tenant)."""
    return service.login_super(db, body)


@router.get("/me", response_model=schemas.MeOut)
def quien_soy(scope: TenantScope = Depends(get_scope), db: Session = Depends(get_db)):
    if scope.is_super:
        sa = db.query(SuperAdmin).filter(SuperAdmin.id == scope.user_id).first()
        if not sa:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Super no existe")
        return schemas.MeOut(
            kind="super",
            user_id=sa.id,
            nombre=sa.nombre,
            email=sa.email,
            roles=["superadmin"],
        )

    user = db.query(User).filter(User.id == scope.user_id).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no existe")
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    return schemas.MeOut(
        kind="tenant",
        user_id=user.id,
        nombre=user.nombre,
        email=user.email,
        roles=[user.rol],
        tenant_id=user.tenant_id,
        tenant_codigo=tenant.codigo if tenant else None,
        tenant_razon_social=tenant.razon_social if tenant else None,
    )
