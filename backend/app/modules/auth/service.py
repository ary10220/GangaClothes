from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.usuarios import Cliente, Rol, Usuario, UsuarioRol


def obtener_roles(db: Session, usuario_id: int) -> list[str]:
    filas = (
        db.query(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .filter(UsuarioRol.usuario_id == usuario_id)
        .all()
    )
    return [r[0] for r in filas]


def asignar_rol(db: Session, usuario_id: int, nombre_rol: str) -> None:
    rol = db.query(Rol).filter(Rol.nombre == nombre_rol).first()
    if rol is None:
        rol = Rol(nombre=nombre_rol)
        db.add(rol)
        db.flush()
    existe = (
        db.query(UsuarioRol)
        .filter(UsuarioRol.usuario_id == usuario_id, UsuarioRol.rol_id == rol.id)
        .first()
    )
    if existe is None:
        db.add(UsuarioRol(usuario_id=usuario_id, rol_id=rol.id))


def _por_email(db: Session, email: str) -> Usuario | None:
    # El correo no distingue mayusculas: Maria@x.com y maria@x.com son la misma cuenta.
    return db.query(Usuario).filter(func.lower(Usuario.email) == email.strip().lower()).first()


def registrar_cliente(db: Session, datos) -> Usuario:
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(400, "El nombre es obligatorio")
    if len(datos.password.encode()) > 72:
        raise HTTPException(400, "La contrasena es demasiado larga (maximo 72 bytes)")
    if _por_email(db, datos.email):
        raise HTTPException(400, "Ya existe una cuenta con ese correo. Inicia sesion o usa otro correo")

    usuario = Usuario(
        nombre=nombre,
        apellido=(datos.apellido or "").strip() or None,
        email=datos.email.strip().lower(),
        password_hash=hash_password(datos.password),
        telefono=(datos.telefono or "").strip() or None,
    )
    db.add(usuario)
    try:
        db.flush()
        db.add(Cliente(usuario_id=usuario.id))
        asignar_rol(db, usuario.id, "cliente")
        db.commit()
    except IntegrityError:
        # Dos registros simultaneos con el mismo correo: la base deja pasar a uno.
        db.rollback()
        raise HTTPException(400, "Ya existe una cuenta con ese correo. Inicia sesion o usa otro correo")
    db.refresh(usuario)
    return usuario


def autenticar(db: Session, email: str, password: str) -> Usuario:
    usuario = _por_email(db, email)
    if usuario is None or not verify_password(password, usuario.password_hash):
        raise HTTPException(401, "Correo o contrasena incorrectos")
    if not usuario.activo:
        raise HTTPException(401, "Usuario inactivo")
    usuario.ultimo_acceso = datetime.utcnow()
    db.commit()
    return usuario
