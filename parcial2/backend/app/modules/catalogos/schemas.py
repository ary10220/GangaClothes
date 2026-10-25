from __future__ import annotations

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# Categoria Schemas
# ==============================================================================
class CategoriaIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)
    activo: bool = True


class CategoriaUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=255)
    activo: bool | None = None


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    activo: bool
    created_at: datetime


# ==============================================================================
# Talla Schemas
# ==============================================================================
class TallaIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    orden: int = 0
    activo: bool = True


class TallaUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    orden: int | None = None
    activo: bool | None = None


class TallaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    orden: int
    activo: bool
    created_at: datetime


# ==============================================================================
# Color Schemas
# ==============================================================================
class ColorIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=50)
    codigo_hex: str | None = Field(default=None, max_length=10)
    activo: bool = True


class ColorUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=50)
    codigo_hex: str | None = Field(default=None, max_length=10)
    activo: bool | None = None


class ColorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    codigo_hex: str | None = None
    activo: bool
    created_at: datetime


# ==============================================================================
# Temporada Schemas
# ==============================================================================
class TemporadaIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool = True


class TemporadaUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool | None = None


class TemporadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool
    created_at: datetime
