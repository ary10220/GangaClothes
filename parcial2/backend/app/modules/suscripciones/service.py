from __future__ import annotations

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import Plan, Producto, Sucursal, Suscripcion, User
from . import schemas



def suscripcion_vigente(db: Session, tenant_id: int) -> tuple[Suscripcion | None, Plan | None]:
    """Devuelve la suscripcion activa del tenant y su plan.
    Se consulta por tenant_id explicito porque esta logica suele correrse
    con scope de superadmin (sin filtro) o fuera de request (seeds).
    """
    row = (
        db.query(Suscripcion, Plan)
        .join(Plan, Plan.id == Suscripcion.plan_id)
        .filter(Suscripcion.tenant_id == tenant_id, Suscripcion.estado == "activa")
        .order_by(Suscripcion.id.desc())
        .first()
    )
    if not row:
        return None, None
    return row[0], row[1]


def _count(db: Session, model, tenant_id: int) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant_id)) or 0)


def consumo(db: Session, tenant_id: int) -> schemas.EstadoSuscripcionOut:
    sub, plan = suscripcion_vigente(db, tenant_id)
    if not sub or not plan:
        return schemas.EstadoSuscripcionOut(tiene_suscripcion=False)

    consumos = [
        schemas.ConsumoLimite.build("sucursales", _count(db, Sucursal, tenant_id), plan.max_sucursales),
        schemas.ConsumoLimite.build("usuarios", _count(db, User, tenant_id), plan.max_usuarios),
        schemas.ConsumoLimite.build("productos", _count(db, Producto, tenant_id), plan.max_productos),
    ]

    return schemas.EstadoSuscripcionOut(
        tiene_suscripcion=True,
        plan=schemas.PlanOut.model_validate(plan),
        fecha_inicio=sub.fecha_inicio,
        fecha_fin=sub.fecha_fin,
        estado=sub.estado,
        consumos=consumos,
        modulos_habilitados=list(plan.modulos or []),
    )


def contratar_plan(db: Session, tenant_id: int, data: schemas.ContratarPlanIn) -> Suscripcion:
    plan = db.query(Plan).filter(Plan.codigo == data.plan_codigo, Plan.activo.is_(True)).first()
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan '{data.plan_codigo}' no existe o esta inactivo")

    # Cerramos cualquier suscripcion activa previa.
    for prev in db.query(Suscripcion).filter(Suscripcion.tenant_id == tenant_id, Suscripcion.estado == "activa").all():
        prev.estado = "cancelada"

    inicio = data.fecha_inicio or date.today()
    nueva = Suscripcion(
        tenant_id=tenant_id,
        plan_id=plan.id,
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(days=data.duracion_dias),
        estado="activa",
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


def exigir_capacidad(db: Session, tenant_id: int, recurso: str) -> tuple[Plan, int, int]:
    """Devuelve (plan, actual, limite) si hay capacidad. Si no, lanza 409 con mensaje claro.
    recurso: 'sucursales' | 'usuarios' | 'productos'.
    """
    sub, plan = suscripcion_vigente(db, tenant_id)
    if not sub or not plan:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La empresa no tiene un plan de suscripcion activo. Contrata un plan antes de continuar.",
        )

    modelo_por_recurso = {"sucursales": Sucursal, "usuarios": User, "productos": Producto}
    limite_por_recurso = {
        "sucursales": plan.max_sucursales,
        "usuarios": plan.max_usuarios,
        "productos": plan.max_productos,
    }

    if recurso not in limite_por_recurso:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Recurso desconocido: {recurso}")

    limite = limite_por_recurso[recurso]
    modelo = modelo_por_recurso[recurso]
    actual = _count(db, modelo, tenant_id)
    if actual >= limite:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Limite alcanzado para {recurso}: {actual} de {limite} segun el plan '{plan.nombre}'. "
            f"Contrata un plan superior para seguir dando de alta {recurso}.",
        )
    return plan, actual, limite

