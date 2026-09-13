from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    # Los largos son los de las columnas de `usuario`.
    nombre: str = Field(min_length=1, max_length=100)
    apellido: str | None = Field(default=None, max_length=100)
    email: EmailStr = Field(max_length=120)
    # bcrypt solo usa los primeros 72 bytes: mas largo se rechaza en el servicio.
    password: str = Field(min_length=6, max_length=72)
    telefono: str | None = Field(default=None, max_length=20, pattern=r"^[0-9+\-\s]{6,20}$")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    apellido: str | None
    email: str
    roles: list[str]
    # Permisos que le llegan por sus roles; la web los usa para saber que puede hacer.
    permisos: list[str] = []


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
