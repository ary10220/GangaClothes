from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProveedorIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    nit: str | None = Field(default=None, max_length=50)
    contacto: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    direccion: str | None = Field(default=None, max_length=255)
    activo: bool = True


class ProveedorUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    nit: str | None = Field(default=None, max_length=50)
    contacto: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    direccion: str | None = Field(default=None, max_length=255)
    estado: str | None = None
    activo: bool | None = None


class ProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nit: str | None = None
    contacto: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    estado: str
    activo: bool
    created_at: datetime
