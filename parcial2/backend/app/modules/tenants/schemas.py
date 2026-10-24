from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field


class TenantAdminIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)


class TenantCreateIn(BaseModel):
    razon_social: str = Field(min_length=2, max_length=200)
    nit: str = Field(min_length=1, max_length=50)
    correo: EmailStr
    telefono: str | None = None
    codigo: str = Field(min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")

    admin: TenantAdminIn
    plan_codigo: str | None = None
    """Si viene, se contrata ese plan al momento del alta."""


class TenantOut(BaseModel):
    id: int
    razon_social: str
    nit: str
    correo: str
    telefono: str | None
    codigo: str
    estado: str
    activo: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class TenantResumenOut(TenantOut):
    plan_actual: str | None = None
    fecha_fin_suscripcion: date | None = None


class TenantUpdateIn(BaseModel):
    razon_social: str | None = Field(default=None, min_length=2, max_length=200)
    correo: EmailStr | None = None
    telefono: str | None = None
    estado: str | None = None
    activo: bool | None = None
