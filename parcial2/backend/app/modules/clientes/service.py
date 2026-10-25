from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...models.cliente import Cliente
from . import schemas


def _get_cliente_mio(db: Session, tenant_id: int, cliente_id: int) -> Cliente:
    cliente = (
        db.query(Cliente)
        .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
        .first()
    )
    if not cliente:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
    return cliente


def listar_clientes(
    db: Session,
    tenant_id: int,
    q: str | None = None,
    tipo: str | None = None,
    activo: bool | None = None,
) -> list[Cliente]:
    query = db.query(Cliente).filter(Cliente.tenant_id == tenant_id)

    if q:
        termino = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Cliente.nombre.ilike(termino),
                Cliente.apellido.ilike(termino),
                Cliente.ci_nit.ilike(termino),
                Cliente.telefono.ilike(termino),
                Cliente.email.ilike(termino),
            )
        )

    if tipo is not None:
        query = query.filter(Cliente.tipo == tipo)

    if activo is not None:
        query = query.filter(Cliente.activo == activo)

    return query.order_by(Cliente.id).all()


def crear_cliente(db: Session, tenant_id: int, data: schemas.ClienteIn) -> Cliente:
    # 1. Validar correo unico dentro del mismo tenant si fue provisto
    if data.email:
        existe_email = (
            db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.email == data.email)
            .first()
        )
        if existe_email:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un cliente con el correo '{data.email}' en esta empresa",
            )

    # 2. Validar CI/NIT unico dentro del mismo tenant si fue provisto
    if data.ci_nit:
        existe_nit = (
            db.query(Cliente)
            .filter(Cliente.tenant_id == tenant_id, Cliente.ci_nit == data.ci_nit)
            .first()
        )
        if existe_nit:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un cliente con el CI/NIT '{data.ci_nit}' en esta empresa",
            )

    cliente = Cliente(
        tenant_id=tenant_id,
        nombre=data.nombre,
        apellido=data.apellido,
        ci_nit=data.ci_nit,
        telefono=data.telefono,
        email=data.email,
        direccion=data.direccion,
        ciudad=data.ciudad,
        tipo=data.tipo,
        notas=data.notas,
        activo=data.activo,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def obtener_cliente(db: Session, tenant_id: int, cliente_id: int) -> Cliente:
    return _get_cliente_mio(db, tenant_id, cliente_id)


def actualizar_cliente(
    db: Session, tenant_id: int, cliente_id: int, data: schemas.ClienteUpdateIn
) -> Cliente:
    cliente = _get_cliente_mio(db, tenant_id, cliente_id)
    payload = data.model_dump(exclude_unset=True)

    if "email" in payload and payload["email"] and payload["email"] != cliente.email:
        existe_email = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.email == payload["email"],
                Cliente.id != cliente_id,
            )
            .first()
        )
        if existe_email:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un cliente con el correo '{payload['email']}' en esta empresa",
            )

    if "ci_nit" in payload and payload["ci_nit"] and payload["ci_nit"] != cliente.ci_nit:
        existe_nit = (
            db.query(Cliente)
            .filter(
                Cliente.tenant_id == tenant_id,
                Cliente.ci_nit == payload["ci_nit"],
                Cliente.id != cliente_id,
            )
            .first()
        )
        if existe_nit:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un cliente con el CI/NIT '{payload['ci_nit']}' en esta empresa",
            )

    for k, v in payload.items():
        setattr(cliente, k, v)

    db.commit()
    db.refresh(cliente)
    return cliente


def eliminar_cliente(db: Session, tenant_id: int, cliente_id: int) -> None:
    cliente = _get_cliente_mio(db, tenant_id, cliente_id)
    db.delete(cliente)
    db.commit()
