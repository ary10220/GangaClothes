from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...core.security import hash_password
from ...models import Plan, Suscripcion, Tenant, User
from . import schemas


def _get_plan_by_codigo(db: Session, codigo: str) -> Plan:
    plan = db.query(Plan).filter(Plan.codigo == codigo, Plan.activo.is_(True)).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan '{codigo}' no existe o esta inactivo")
    return plan


def crear_tenant(db: Session, data: schemas.TenantCreateIn) -> Tenant:
    """CU-01. Crea empresa + admin inicial + (opcional) suscripcion al plan indicado."""
    if db.query(Tenant).filter(Tenant.codigo == data.codigo).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un tenant con codigo '{data.codigo}'")
    if db.query(Tenant).filter(Tenant.nit == data.nit).first():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un tenant con NIT '{data.nit}'")

    tenant = Tenant(
        razon_social=data.razon_social,
        nit=data.nit,
        correo=data.correo,
        telefono=data.telefono,
        codigo=data.codigo,
        estado="activo",
        activo=True,
    )
    db.add(tenant)
    db.flush()

    admin = User(
        tenant_id=tenant.id,
        email=data.admin.email,
        password_hash=hash_password(data.admin.password),
        nombre=data.admin.nombre,
        rol="admin",
        estado="activo",
        activo=True,
    )
    db.add(admin)

    if data.plan_codigo:
        plan = _get_plan_by_codigo(db, data.plan_codigo)
        hoy = date.today()
        sub = Suscripcion(
            tenant_id=tenant.id,
            plan_id=plan.id,
            fecha_inicio=hoy,
            fecha_fin=hoy + timedelta(days=30),
            estado="activa",
        )
        db.add(sub)

    db.commit()
    db.refresh(tenant)
    return tenant


def listar_tenants(db: Session) -> list[Tenant]:
    return db.query(Tenant).order_by(Tenant.id).all()


def obtener_tenant(db: Session, tenant_id: int) -> Tenant:
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant no encontrado")
    return t


def actualizar_tenant(db: Session, tenant_id: int, data: schemas.TenantUpdateIn) -> Tenant:
    t = obtener_tenant(db, tenant_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t
