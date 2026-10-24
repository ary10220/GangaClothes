from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...models import Sucursal
from ..suscripciones.service import exigir_capacidad
from . import schemas


def _get_mia(db: Session, tenant_id: int, sucursal_id: int) -> Sucursal:
    """Devuelve la sucursal del scope. El filtro central ya restringe a tenant_id,
    pero reforzamos el WHERE para que las consultas de superadmin con un scope de tenant
    (por si alguna vez damos ese caso) tambien queden limitadas.
    """
    s = db.query(Sucursal).filter(Sucursal.id == sucursal_id, Sucursal.tenant_id == tenant_id).first()
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sucursal no encontrada")
    return s


def listar(db: Session, tenant_id: int) -> list[Sucursal]:
    return db.query(Sucursal).filter(Sucursal.tenant_id == tenant_id).order_by(Sucursal.id).all()


def crear(db: Session, tenant_id: int, data: schemas.SucursalIn) -> Sucursal:
    exigir_capacidad(db, tenant_id, "sucursales")

    existe = (
        db.query(Sucursal)
        .filter(Sucursal.tenant_id == tenant_id, Sucursal.codigo == data.codigo)
        .first()
    )
    if existe:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe una sucursal con codigo '{data.codigo}'")

    s = Sucursal(
        tenant_id=tenant_id,
        codigo=data.codigo,
        nombre=data.nombre,
        ciudad=data.ciudad,
        direccion=data.direccion,
        horario=data.horario,
        estado="activa",
        activo=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def obtener(db: Session, tenant_id: int, sucursal_id: int) -> Sucursal:
    return _get_mia(db, tenant_id, sucursal_id)


def actualizar(db: Session, tenant_id: int, sucursal_id: int, data: schemas.SucursalUpdateIn) -> Sucursal:
    s = _get_mia(db, tenant_id, sucursal_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


def eliminar(db: Session, tenant_id: int, sucursal_id: int) -> None:
    s = _get_mia(db, tenant_id, sucursal_id)
    db.delete(s)
    db.commit()
