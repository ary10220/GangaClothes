from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ...core.deps import get_db, require_super
from ...core.database import TenantScope
from ...models import Plan, Suscripcion, Tenant
from . import schemas, service


router = APIRouter(prefix="/tenants", tags=["CU-01 Tenants"])


@router.post("", response_model=schemas.TenantOut, status_code=status.HTTP_201_CREATED)
def crear_empresa_contratante(
    body: schemas.TenantCreateIn,
    _: TenantScope = Depends(require_super),
    db: Session = Depends(get_db),
):
    """CU-01: Alta de empresa contratante con su administrador inicial y plan opcional.
    Solo el superadministrador de plataforma puede ejecutarlo.
    """
    return service.crear_tenant(db, body)


@router.get("", response_model=list[schemas.TenantResumenOut])
def listar_empresas(
    _: TenantScope = Depends(require_super),
    db: Session = Depends(get_db),
):
    tenants = service.listar_tenants(db)
    resumen = []
    for t in tenants:
        sub = (
            db.query(Suscripcion, Plan)
            .join(Plan, Plan.id == Suscripcion.plan_id)
            .filter(Suscripcion.tenant_id == t.id, Suscripcion.estado == "activa")
            .first()
        )
        plan_nombre = sub[1].nombre if sub else None
        fecha_fin = sub[0].fecha_fin if sub else None
        resumen.append(
            schemas.TenantResumenOut(
                id=t.id,
                razon_social=t.razon_social,
                nit=t.nit,
                correo=t.correo,
                telefono=t.telefono,
                codigo=t.codigo,
                estado=t.estado,
                activo=t.activo,
                created_at=t.created_at,
                plan_actual=plan_nombre,
                fecha_fin_suscripcion=fecha_fin,
            )
        )
    return resumen


@router.get("/{tenant_id}", response_model=schemas.TenantOut)
def ver_empresa(
    tenant_id: int,
    _: TenantScope = Depends(require_super),
    db: Session = Depends(get_db),
):
    return service.obtener_tenant(db, tenant_id)


@router.patch("/{tenant_id}", response_model=schemas.TenantOut)
def actualizar_empresa(
    tenant_id: int,
    body: schemas.TenantUpdateIn,
    _: TenantScope = Depends(require_super),
    db: Session = Depends(get_db),
):
    return service.actualizar_tenant(db, tenant_id, body)
