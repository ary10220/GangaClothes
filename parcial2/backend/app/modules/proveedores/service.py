from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...models import Proveedor
from . import schemas


def _get_mio(db: Session, tenant_id: int, proveedor_id: int) -> Proveedor:
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id, Proveedor.tenant_id == tenant_id).first()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proveedor no encontrado")
    return p


def listar(db: Session, tenant_id: int) -> list[Proveedor]:
    return db.query(Proveedor).filter(Proveedor.tenant_id == tenant_id).order_by(Proveedor.id).all()


def crear(db: Session, tenant_id: int, data: schemas.ProveedorIn) -> Proveedor:
    existe = (
        db.query(Proveedor)
        .filter(Proveedor.tenant_id == tenant_id, Proveedor.nombre == data.nombre)
        .first()
    )
    if existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe un proveedor con el nombre '{data.nombre}'",
        )

    proveedor = Proveedor(
        tenant_id=tenant_id,
        nombre=data.nombre,
        nit=data.nit,
        contacto=data.contacto,
        telefono=data.telefono,
        email=data.email,
        direccion=data.direccion,
        estado="activo",
        activo=data.activo,
    )
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


def obtener(db: Session, tenant_id: int, proveedor_id: int) -> Proveedor:
    return _get_mio(db, tenant_id, proveedor_id)


def actualizar(
    db: Session, tenant_id: int, proveedor_id: int, data: schemas.ProveedorUpdateIn
) -> Proveedor:
    prov = _get_mio(db, tenant_id, proveedor_id)
    payload = data.model_dump(exclude_unset=True)

    if "nombre" in payload and payload["nombre"] != prov.nombre:
        existe = (
            db.query(Proveedor)
            .filter(
                Proveedor.tenant_id == tenant_id,
                Proveedor.nombre == payload["nombre"],
                Proveedor.id != proveedor_id,
            )
            .first()
        )
        if existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un proveedor con el nombre '{payload['nombre']}'",
            )

    for k, v in payload.items():
        setattr(prov, k, v)

    db.commit()
    db.refresh(prov)
    return prov


def eliminar(db: Session, tenant_id: int, proveedor_id: int) -> None:
    prov = _get_mio(db, tenant_id, proveedor_id)
    db.delete(prov)
    db.commit()
