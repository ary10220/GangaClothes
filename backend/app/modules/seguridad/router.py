"""Roles con sus permisos y consulta de la bitacora.

El rol llamado "administrador" es intencionalmente inmutable: si se le pudieran
quitar permisos o borrarlo, nadie podria volver a entrar a administrar roles y
habria que arreglarlo a mano en la base de datos.
"""
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.core import permisos as cat
from app.core.auditoria import registrar
from app.core.deps import get_db, require_permiso
from app.models.seguridad import Bitacora, Permiso, RolPermiso
from app.models.usuarios import Rol, UsuarioRol

router = APIRouter()

ROL_INTOCABLE = "administrador"

ver_roles = require_permiso("roles:ver")
crear_roles = require_permiso("roles:crear")
editar_roles = require_permiso("roles:editar")
eliminar_roles = require_permiso("roles:eliminar")
ver_bitacora = require_permiso("bitacora:ver")


class RolIn(BaseModel):
    nombre: str = Field(min_length=3, max_length=50)
    descripcion: str | None = None
    permisos: list[str] = []


class RolUpd(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=50)
    descripcion: str | None = None
    activo: bool | None = None
    permisos: list[str] | None = None


def _permisos_de_rol(db, rol_id: int) -> list[str]:
    filas = (
        db.query(Permiso.codigo)
        .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
        .filter(RolPermiso.rol_id == rol_id)
        .all()
    )
    return sorted(f[0] for f in filas)


def _salida_rol(db, rol: Rol) -> dict:
    usuarios = db.query(func.count(UsuarioRol.id)).filter(UsuarioRol.rol_id == rol.id).scalar()
    return {
        "id": rol.id,
        "nombre": rol.nombre,
        "descripcion": rol.descripcion,
        "activo": bool(rol.activo),
        "usuarios": usuarios or 0,
        "permisos": _permisos_de_rol(db, rol.id),
        "editable": rol.nombre != ROL_INTOCABLE,
    }


def _aplicar_permisos(db, rol: Rol, codigos: list[str]) -> None:
    """Reemplaza los permisos del rol por los codigos indicados."""
    validos = {p.codigo: p.id for p in db.query(Permiso).all()}
    desconocidos = [c for c in codigos if c not in validos]
    if desconocidos:
        raise HTTPException(400, f"Permisos inexistentes: {', '.join(desconocidos)}")
    db.query(RolPermiso).filter(RolPermiso.rol_id == rol.id).delete()
    for codigo in dict.fromkeys(codigos):
        db.add(RolPermiso(rol_id=rol.id, permiso_id=validos[codigo]))


# ------------------------------------------------------------------ permisos
@router.get("/permisos", summary="Catalogo de permisos agrupado por modulo")
def listar_permisos(db=Depends(get_db), _=Depends(ver_roles)):
    filas = db.query(Permiso).all()
    por_modulo: dict[str, list[dict]] = {}
    for p in filas:
        por_modulo.setdefault(p.modulo, []).append({
            "codigo": p.codigo, "accion": p.accion,
            "nombre": p.nombre, "descripcion": p.descripcion,
        })
    # Se devuelve en el orden declarado en core/permisos.py, no el de la base.
    salida = []
    for modulo, (etiqueta, descripcion, acciones) in cat.MODULOS.items():
        if modulo not in por_modulo:
            continue
        orden = {a: i for i, a in enumerate(acciones)}
        salida.append({
            "modulo": modulo,
            "etiqueta": etiqueta,
            "descripcion": descripcion,
            "permisos": sorted(por_modulo[modulo], key=lambda p: orden.get(p["accion"], 99)),
        })
    return salida


# --------------------------------------------------------------------- roles
@router.get("/roles", summary="Roles con sus permisos y cuantos usuarios los tienen")
def listar_roles(db=Depends(get_db), _=Depends(ver_roles)):
    return [_salida_rol(db, r) for r in db.query(Rol).order_by(Rol.id).all()]


@router.post("/roles", status_code=201, summary="Crear rol")
def crear_rol(datos: RolIn, peticion: Request, db=Depends(get_db), usuario=Depends(crear_roles)):
    nombre = datos.nombre.strip().lower()
    if db.query(Rol).filter(func.lower(Rol.nombre) == nombre).first():
        raise HTTPException(400, "Ya existe un rol con ese nombre")
    rol = Rol(nombre=nombre, descripcion=datos.descripcion)
    db.add(rol)
    db.flush()
    _aplicar_permisos(db, rol, datos.permisos)
    db.commit()
    db.refresh(rol)
    registrar(db, modulo="ROLES", accion="CREAR", usuario=usuario, peticion=peticion,
              entidad="rol", entidad_id=rol.id,
              detalle=f"Rol '{rol.nombre}' con {len(datos.permisos)} permisos")
    return _salida_rol(db, rol)


@router.put("/roles/{id}", summary="Editar rol y reasignar sus permisos")
def editar_rol(id: int, datos: RolUpd, peticion: Request, db=Depends(get_db), usuario=Depends(editar_roles)):
    rol = db.get(Rol, id)
    if rol is None:
        raise HTTPException(404, "Rol no encontrado")
    if rol.nombre == ROL_INTOCABLE:
        raise HTTPException(400, "El rol administrador no se puede modificar: siempre tiene acceso total")

    cambios = datos.model_dump(exclude_unset=True)
    codigos = cambios.pop("permisos", None)

    if "nombre" in cambios and cambios["nombre"]:
        nuevo = cambios["nombre"].strip().lower()
        otro = db.query(Rol).filter(func.lower(Rol.nombre) == nuevo, Rol.id != id).first()
        if otro:
            raise HTTPException(400, "Ya existe un rol con ese nombre")
        cambios["nombre"] = nuevo

    for k, v in cambios.items():
        setattr(rol, k, v)
    if codigos is not None:
        _aplicar_permisos(db, rol, codigos)
    db.commit()
    db.refresh(rol)

    detalle = f"Rol '{rol.nombre}'"
    if codigos is not None:
        detalle += f": {len(codigos)} permisos asignados"
    registrar(db, modulo="ROLES", accion="EDITAR", usuario=usuario, peticion=peticion,
              entidad="rol", entidad_id=rol.id, detalle=detalle)
    return _salida_rol(db, rol)


@router.delete("/roles/{id}", summary="Eliminar rol (se desactiva si tiene usuarios)")
def eliminar_rol(id: int, peticion: Request, db=Depends(get_db), usuario=Depends(eliminar_roles)):
    rol = db.get(Rol, id)
    if rol is None:
        raise HTTPException(404, "Rol no encontrado")
    if rol.nombre == ROL_INTOCABLE:
        raise HTTPException(400, "El rol administrador no se puede eliminar")

    asignados = db.query(func.count(UsuarioRol.id)).filter(UsuarioRol.rol_id == rol.id).scalar() or 0
    if asignados:
        rol.activo = False
        db.commit()
        registrar(db, modulo="ROLES", accion="EDITAR", usuario=usuario, peticion=peticion,
                  entidad="rol", entidad_id=id, nivel="ALERTA",
                  detalle=f"Rol '{rol.nombre}' desactivado: lo usan {asignados} usuarios")
        return {"detail": f"El rol lo usan {asignados} usuarios: se desactivo en su lugar"}

    nombre = rol.nombre
    db.query(RolPermiso).filter(RolPermiso.rol_id == id).delete()
    db.delete(rol)
    db.commit()
    registrar(db, modulo="ROLES", accion="ELIMINAR", usuario=usuario, peticion=peticion,
              entidad="rol", entidad_id=id, nivel="ALERTA", detalle=f"Rol '{nombre}' eliminado")
    return {"detail": "rol eliminado"}


# ------------------------------------------------------------------ bitacora
@router.get("/bitacora", summary="Registro de acciones del sistema")
def listar_bitacora(
    modulo: str | None = None,
    accion: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(200, ge=1, le=1000),
    db=Depends(get_db),
    _=Depends(ver_bitacora),
):
    consulta = db.query(Bitacora)
    if modulo:
        consulta = consulta.filter(Bitacora.modulo == modulo.upper())
    if accion:
        consulta = consulta.filter(Bitacora.accion == accion.upper())
    if desde:
        consulta = consulta.filter(Bitacora.fecha >= datetime.combine(desde, time.min))
    if hasta:
        consulta = consulta.filter(Bitacora.fecha <= datetime.combine(hasta, time.max))

    filas = consulta.order_by(Bitacora.fecha.desc(), Bitacora.id.desc()).limit(limite).all()
    return [{
        "id": f.id,
        "fecha": f.fecha.isoformat() if f.fecha else None,
        "actor": f.actor,
        "modulo": f.modulo,
        "accion": f.accion,
        "nivel": f.nivel,
        "entidad": f.entidad,
        "entidad_id": f.entidad_id,
        "detalle": f.detalle,
        "ip": f.ip,
    } for f in filas]


@router.get("/bitacora/filtros", summary="Modulos y acciones presentes en la bitacora")
def filtros_bitacora(db=Depends(get_db), _=Depends(ver_bitacora)):
    modulos = [f[0] for f in db.query(Bitacora.modulo).distinct().order_by(Bitacora.modulo).all()]
    acciones = [f[0] for f in db.query(Bitacora.accion).distinct().order_by(Bitacora.accion).all()]
    return {"modulos": modulos, "acciones": acciones}
