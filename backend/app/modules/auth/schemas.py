from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    nombre: str
    apellido: str | None = None
    email: EmailStr
    password: str = Field(min_length=6)
    telefono: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    apellido: str | None
    email: str
    roles: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
