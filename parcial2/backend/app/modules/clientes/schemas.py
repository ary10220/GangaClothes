from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ClienteIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    apellido: str | None = Field(default=None, max_length=100)
    ci_nit: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=150)
    direccion: str | None = Field(default=None, max_length=255)
    ciudad: str | None = Field(default=None, max_length=80)
    tipo: str = Field(default="regular", max_length=30)  # regular | mayorista | vip
    notas: str | None = Field(default=None, max_length=500)
    activo: bool = True


class ClienteUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    apellido: str | None = Field(default=None, max_length=100)
    ci_nit: str | None = Field(default=None, max_length=30)
    telefono: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=150)
    direccion: str | None = Field(default=None, max_length=255)
    ciudad: str | None = Field(default=None, max_length=80)
    tipo: str | None = Field(default=None, max_length=30)
    notas: str | None = Field(default=None, max_length=500)
    activo: bool | None = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    nombre: str
    apellido: str | None = None
    ci_nit: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    tipo: str
    notas: str | None = None
    activo: bool
    created_at: datetime
