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
