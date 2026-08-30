from datetime import datetime

from fastapi import HTTPException
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


def registrar_cliente(db: Session, datos) -> Usuario:
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(400, "Ya existe un usuario con ese correo")
    usuario = Usuario(
        nombre=datos.nombre,
        apellido=datos.apellido,
        email=datos.email,
        password_hash=hash_password(datos.password),
        telefono=datos.telefono,
    )
    db.add(usuario)
    db.flush()
    db.add(Cliente(usuario_id=usuario.id))
    asignar_rol(db, usuario.id, "cliente")
    db.commit()
    db.refresh(usuario)
    return usuario


def autenticar(db: Session, email: str, password: str) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None or not verify_password(password, usuario.password_hash):
        raise HTTPException(401, "Correo o contrasena incorrectos")
    if not usuario.activo:
        raise HTTPException(401, "Usuario inactivo")
    usuario.ultimo_acceso = datetime.utcnow()
    db.commit()
    return usuario
