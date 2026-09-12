from fastapi import APIRouter, Depends, Request

from app.core.auditoria import registrar
from app.core.deps import get_current_user, get_db, permisos_de
from app.core.security import create_token
from app.modules.auth import service
from app.modules.auth.schemas import LoginIn, RegisterIn, TokenOut, UsuarioOut

router = APIRouter()


def _token_out(db, usuario) -> TokenOut:
    roles = service.obtener_roles(db, usuario.id)
    return TokenOut(
        access_token=create_token(usuario.id, roles),
        usuario=UsuarioOut(
            id=usuario.id, nombre=usuario.nombre, apellido=usuario.apellido,
            email=usuario.email, roles=roles,
            permisos=sorted(permisos_de(db, usuario.id)),
        ),
    )


@router.post("/register", response_model=TokenOut, summary="CU20: registro de cliente")
def register(datos: RegisterIn, db=Depends(get_db)):
    usuario = service.registrar_cliente(db, datos)
    return _token_out(db, usuario)


@router.post("/login", response_model=TokenOut, summary="CU1 / CU20: iniciar sesion")
def login(datos: LoginIn, peticion: Request, db=Depends(get_db)):
    usuario = service.autenticar(db, datos.email, datos.password)
    salida = _token_out(db, usuario)
    registrar(db, modulo="SESION", accion="INGRESO", usuario=usuario, peticion=peticion,
              entidad="usuario", entidad_id=usuario.id,
              detalle=f"Inicio de sesion como {', '.join(salida.usuario.roles) or 'sin rol'}")
    return salida


@router.post("/logout", summary="CU2: cerrar sesion")
def logout(peticion: Request, usuario=Depends(get_current_user), db=Depends(get_db)):
    """El token es sin estado: la web lo descarta igual. Esto existe para que
    el cierre de sesion quede registrado en la bitacora."""
    registrar(db, modulo="SESION", accion="SALIDA", usuario=usuario, peticion=peticion,
              entidad="usuario", entidad_id=usuario.id, detalle="Cierre de sesion")
    return {"detail": "Sesion cerrada"}


@router.get("/me", response_model=UsuarioOut, summary="Usuario autenticado actual")
def me(usuario=Depends(get_current_user), db=Depends(get_db)):
    return UsuarioOut(
        id=usuario.id, nombre=usuario.nombre, apellido=usuario.apellido,
        email=usuario.email, roles=service.obtener_roles(db, usuario.id),
        permisos=sorted(permisos_de(db, usuario.id)),
    )
