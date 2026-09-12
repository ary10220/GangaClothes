"""CU3: administrar usuarios y roles (Integrante 1, Iteracion 1)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.core.security import hash_password
from app.models.usuarios import Usuario, UsuarioRol
from app.modules.auth.service import asignar_rol, obtener_roles

router = APIRouter()
ver = require_permiso("usuarios:ver")
crear_u = require_permiso("usuarios:crear")
editar_u = require_permiso("usuarios:editar")


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
def listar(db=Depends(get_db), _=Depends(ver)):
    return [_salida(db, u) for u in db.query(Usuario).all()]


@router.post("", status_code=201, summary="Crear usuario con roles")
def crear(datos: UsuarioCrear, peticion: Request, db=Depends(get_db), usuario=Depends(crear_u)):
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(400, "Ya existe un usuario con ese correo")
    u = Usuario(nombre=datos.nombre, apellido=datos.apellido, email=datos.email,
                password_hash=hash_password(datos.password), telefono=datos.telefono)
    db.add(u)
    db.flush()
    for rol in datos.roles:
        asignar_rol(db, u.id, rol)
    db.commit()
    registrar(db, modulo="USUARIOS", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="usuario", entidad_id=u.id,
              detalle=f"Alta de {u.email} con roles: {', '.join(datos.roles) or 'ninguno'}")
    return _salida(db, u)


@router.put("/{id}", summary="Editar usuario / reasignar roles")
def editar(id: int, datos: UsuarioEditar, peticion: Request, db=Depends(get_db),
           usuario=Depends(editar_u)):
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
    if list(cambios) == ["activo"]:
        detalle = f"{'Reactivacion' if cambios['activo'] else 'Archivado'} de {u.email}"
    else:
        partes = list(cambios) + ([f"roles: {', '.join(roles)}"] if roles is not None else [])
        detalle = f"Cambios en {u.email}: {', '.join(partes) or 'sin cambios'}"
    registrar(db, modulo="USUARIOS", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="usuario", entidad_id=u.id, detalle=detalle)
    return _salida(db, u)
