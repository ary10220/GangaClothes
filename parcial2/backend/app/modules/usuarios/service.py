from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ...core.security import hash_password
from ...models import User
from ..suscripciones.service import exigir_capacidad
from . import schemas


def _get_mio(db: Session, tenant_id: int, user_id: int) -> User:
    u = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return u


def listar(db: Session, tenant_id: int) -> list[User]:
    return db.query(User).filter(User.tenant_id == tenant_id).order_by(User.id).all()


def crear(db: Session, tenant_id: int, data: schemas.UsuarioIn) -> User:
    # 1. Comprobar limite de usuarios segun el plan contratado
    exigir_capacidad(db, tenant_id, "usuarios")

    # 2. Comprobar que el correo no este duplicado dentro de la misma empresa
    existe = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.email == data.email)
        .first()
    )
    if existe:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya existe un usuario con correo '{data.email}' en esta empresa",
        )

    user = User(
        tenant_id=tenant_id,
        nombre=data.nombre,
        apellido=data.apellido,
        email=data.email,
        password_hash=hash_password(data.password),
        telefono=data.telefono,
        rol=data.rol,
        estado="activo",
        activo=data.activo,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def obtener(db: Session, tenant_id: int, user_id: int) -> User:
    return _get_mio(db, tenant_id, user_id)


def actualizar(
    db: Session, tenant_id: int, user_id: int, data: schemas.UsuarioUpdateIn
) -> User:
    user = _get_mio(db, tenant_id, user_id)
    payload = data.model_dump(exclude_unset=True, exclude={"roles"})

    if "email" in payload and payload["email"] != user.email:
        existe = (
            db.query(User)
            .filter(
                User.tenant_id == tenant_id,
                User.email == payload["email"],
                User.id != user_id,
            )
            .first()
        )
        if existe:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya existe un usuario con correo '{payload['email']}' en esta empresa",
            )

    if "password" in payload and payload["password"]:
        user.password_hash = hash_password(payload.pop("password"))
    elif "password" in payload:
        payload.pop("password")

    for k, v in payload.items():
        setattr(user, k, v)

    db.commit()
    db.refresh(user)
    return user


def eliminar(db: Session, tenant_id: int, user_id: int, current_user_id: int | None = None) -> None:
    if current_user_id is not None and user_id == current_user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No puedes eliminar tu propia cuenta de usuario",
        )
    user = _get_mio(db, tenant_id, user_id)
    db.delete(user)
    db.commit()
