"""CU3: administrar usuarios y roles (Integrante 1, Iteracion 1)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

from app.core.auditoria import registrar
from app.core.contrasenas import exigir_segura
from app.core.deps import get_db, require_permiso
from app.core.security import hash_password
from app.models.usuarios import Usuario, UsuarioRol
from app.modules.auth.service import asignar_rol, obtener_roles
from app.modules.proveedores import service as proveedores

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
    # CU9: proveedor cuya oferta administra esta cuenta (solo con el rol proveedor).
    proveedor_id: int | None = None


class UsuarioEditar(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    telefono: str | None = None
    activo: bool | None = None
    roles: list[str] | None = None
    proveedor_id: int | None = None


def _salida(db, u: Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "apellido": u.apellido, "email": u.email,
            "telefono": u.telefono, "activo": u.activo, "roles": obtener_roles(db, u.id),
            "proveedor": proveedores.proveedor_del_usuario(db, u.id)}


def _enlazar_proveedor(db, u: Usuario, roles: list[str], proveedor_id: int | None) -> None:
    """Sin el rol proveedor la cuenta no queda enlazada a ninguno."""
    if "proveedor" not in roles:
        proveedores.enlazar_usuario(db, u.id, None)
        return
    if proveedor_id is None:
        raise HTTPException(400, "Una cuenta con rol proveedor necesita el proveedor al que pertenece")
    proveedores.enlazar_usuario(db, u.id, proveedor_id)


@router.get("", summary="Listar usuarios")
def listar(db=Depends(get_db), _=Depends(ver)):
    return [_salida(db, u) for u in db.query(Usuario).all()]


@router.post("", status_code=201, summary="Crear usuario con roles")
def crear(datos: UsuarioCrear, peticion: Request, db=Depends(get_db), usuario=Depends(crear_u)):
    if db.query(Usuario).filter(Usuario.email == datos.email).first():
        raise HTTPException(400, "Ya existe un usuario con ese correo")
    exigir_segura(datos.password)
    u = Usuario(nombre=datos.nombre, apellido=datos.apellido, email=datos.email,
                password_hash=hash_password(datos.password), telefono=datos.telefono)
    db.add(u)
    db.flush()
    for rol in datos.roles:
        asignar_rol(db, u.id, rol)
    try:
        _enlazar_proveedor(db, u, datos.roles, datos.proveedor_id)
    except HTTPException:
        db.rollback()
        raise
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
    toca_proveedor = "proveedor_id" in cambios
    proveedor_id = cambios.pop("proveedor_id", None)
    for k, v in cambios.items():
        setattr(u, k, v)
    if roles is not None:
        db.query(UsuarioRol).filter(UsuarioRol.usuario_id == u.id).delete()
        for rol in roles:
            asignar_rol(db, u.id, rol)
    if roles is not None or toca_proveedor:
        db.flush()
        actual = proveedores.proveedor_del_usuario(db, u.id)
        try:
            _enlazar_proveedor(db, u, roles if roles is not None else obtener_roles(db, u.id),
                               proveedor_id if toca_proveedor else (actual["id"] if actual else None))
        except HTTPException:
            db.rollback()
            raise
    db.commit()
    if list(cambios) == ["activo"]:
        detalle = f"{'Reactivacion' if cambios['activo'] else 'Archivado'} de {u.email}"
    else:
        partes = list(cambios) + ([f"roles: {', '.join(roles)}"] if roles is not None else [])
        detalle = f"Cambios en {u.email}: {', '.join(partes) or 'sin cambios'}"
    registrar(db, modulo="USUARIOS", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="usuario", entidad_id=u.id, detalle=detalle)
    return _salida(db, u)
