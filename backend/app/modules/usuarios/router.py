"""CU3: administrar usuarios y roles (Integrante 1, Iteracion 1)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.deps import get_db, require_roles
from app.core.security import hash_password
from app.models.usuarios import Usuario, UsuarioRol
from app.modules.auth.service import asignar_rol, obtener_roles

router = APIRouter()
admin = require_roles("administrador")


class UsuarioCrear(BaseModel):
    nombre: str
    apellido: str | None = None
    email: EmailStr
    password: str
    telefono: str | None = None
    roles: list[str] = ["cliente"]


class UsuarioEditar(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    telefono: str | None = None
    activo: bool | None = None
    roles: list[str] | None = None


def _salida(db, u: Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "apellido": u.apellido, "email": u.email,
            "telefono": u.telefono, "activo": u.activo, "roles": obtener_roles(db, u.id)}


@router.get("", summary="Listar usuarios")
def listar(db=Depends(get_db), _=Depends(admin)):
    return [_salida(db, u) for u in db.query(Usuario).all()]


@router.post("", status_code=201, summary="Crear usuario con roles")
def crear(datos: UsuarioCrear, db=Depends(get_db), _=Depends(admin)):
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(400, "Ya existe un usuario con ese correo")
    u = Usuario(nombre=datos.nombre, apellido=datos.apellido, email=datos.email,
                password_hash=hash_password(datos.password), telefono=datos.telefono)
    db.add(u)
    db.flush()
    for rol in datos.roles:
        asignar_rol(db, u.id, rol)
    db.commit()
    return _salida(db, u)


@router.put("/{id}", summary="Editar usuario / reasignar roles")
def editar(id: int, datos: UsuarioEditar, db=Depends(get_db), _=Depends(admin)):
    u = db.get(Usuario, id)
    if u is None:
        raise HTTPException(404, "Usuario no encontrado")
    cambios = datos.model_dump(exclude_unset=True)
    roles = cambios.pop("roles", None)
    for k, v in cambios.items():
        setattr(u, k, v)
    if roles is not None:
        db.query(UsuarioRol).filter(UsuarioRol.usuario_id == u.id).delete()
        for rol in roles:
            asignar_rol(db, u.id, rol)
    db.commit()
    return _salida(db, u)
