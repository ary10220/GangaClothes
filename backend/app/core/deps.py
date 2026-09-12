from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.database import SessionLocal
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(bearer), db=Depends(get_db)
):
    from app.models.usuarios import Usuario

    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token requerido")
    try:
        payload = decode_token(cred.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido o expirado")
    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")
    usuario.roles_token = payload.get("roles", [])
    return usuario


def require_roles(*roles: str):
    """Uso: Depends(require_roles('administrador', 'encargado'))"""

    def dep(usuario=Depends(get_current_user)):
        if not set(roles) & set(getattr(usuario, "roles_token", [])):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permisos para esta operacion")
        return usuario

    return dep


def permisos_de(db, usuario_id: int) -> set[str]:
    """Todos los permisos que le llegan al usuario a traves de sus roles."""
    from app.models.seguridad import Permiso, RolPermiso
    from app.models.usuarios import Rol, UsuarioRol

    filas = (
        db.query(Permiso.codigo)
        .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
        .join(Rol, Rol.id == RolPermiso.rol_id)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .filter(UsuarioRol.usuario_id == usuario_id, Rol.activo == True)  # noqa: E712
        .all()
    )
    return {f[0] for f in filas}


def require_permiso(*codigos: str):
    """Exige que el usuario tenga alguno de estos permisos.

    Uso: Depends(require_permiso('prendas:crear'))

    A diferencia de require_roles, no mira el nombre del rol sino los permisos
    que ese rol tiene asignados. Es lo que hace que la pantalla de roles sirva
    de verdad: cambiar ahi un permiso cambia el acceso al endpoint.
    """

    def dep(usuario=Depends(get_current_user), db=Depends(get_db)):
        if not set(codigos) & permisos_de(db, usuario.id):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Tu rol no tiene el permiso necesario ({', '.join(codigos)})",
            )
        return usuario

    return dep
