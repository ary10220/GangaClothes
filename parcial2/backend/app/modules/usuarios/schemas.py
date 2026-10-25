from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UsuarioIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    apellido: str | None = Field(default=None, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=200)
    telefono: str | None = Field(default=None, max_length=50)
    rol: str = "cajero"
    roles: list[str] | None = None
    activo: bool = True

    @model_validator(mode="after")
    def resolver_roles(self) -> UsuarioIn:
        if self.roles and len(self.roles) > 0:
            self.rol = self.roles[0]
        return self


class UsuarioUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=200)
    apellido: str | None = Field(default=None, max_length=200)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=200)
    telefono: str | None = Field(default=None, max_length=50)
    rol: str | None = None
    roles: list[str] | None = None
    estado: str | None = None
    activo: bool | None = None

    @model_validator(mode="after")
    def resolver_roles(self) -> UsuarioUpdateIn:
        if self.roles and len(self.roles) > 0:
            self.rol = self.roles[0]
        return self


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str | None = None
    email: str
    telefono: str | None = None
    rol: str
    roles: list[str] = Field(default_factory=list)
    estado: str
    activo: bool
    created_at: datetime

    @model_validator(mode="after")
    def sincronizar_roles(self) -> UsuarioOut:
        if not self.roles and self.rol:
            self.roles = [self.rol]
        return self
