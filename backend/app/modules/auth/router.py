from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, get_db
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
        ),
    )


@router.post("/register", response_model=TokenOut, summary="CU20: registro de cliente")
def register(datos: RegisterIn, db=Depends(get_db)):
    usuario = service.registrar_cliente(db, datos)
    return _token_out(db, usuario)


@router.post("/login", response_model=TokenOut, summary="CU1 / CU20: iniciar sesion")
def login(datos: LoginIn, db=Depends(get_db)):
    usuario = service.autenticar(db, datos.email, datos.password)
    return _token_out(db, usuario)


@router.get("/me", response_model=UsuarioOut, summary="Usuario autenticado actual")
def me(usuario=Depends(get_current_user), db=Depends(get_db)):
    return UsuarioOut(
        id=usuario.id, nombre=usuario.nombre, apellido=usuario.apellido,
        email=usuario.email, roles=service.obtener_roles(db, usuario.id),
    )
