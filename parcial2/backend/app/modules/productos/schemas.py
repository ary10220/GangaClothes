from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from ..catalogos.schemas import ColorOut, TallaOut


# ==============================================================================
# Variante Schemas
# ==============================================================================
class VarianteIn(BaseModel):
    talla_id: int
    color_id: int
    sku: str | None = Field(default=None, max_length=60)
    precio_adicional: float = Field(default=0.0, ge=0)
    imagen_url: str | None = Field(default=None, max_length=255)
    activo: bool = True


class VarianteUpdateIn(BaseModel):
    sku: str | None = Field(default=None, max_length=60)
    precio_adicional: float | None = Field(default=None, ge=0)
    imagen_url: str | None = Field(default=None, max_length=255)
    activo: bool | None = None


class VarianteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    talla_id: int
    color_id: int
    sku: str
    precio_adicional: float
    imagen_url: str | None = None
    activo: bool
    created_at: datetime

    talla: TallaOut | None = None
    color: ColorOut | None = None


# ==============================================================================
# Producto Schemas
# ==============================================================================
class ProductoIn(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    categoria_id: int
    temporada_id: int | None = None
    proveedor_id: int | None = None
    descripcion: str | None = Field(default=None, max_length=500)
    marca: str | None = Field(default=None, max_length=80)
    genero: str | None = Field(default=None, max_length=30)
    precio_venta: float = Field(..., ge=0)
    costo: float = Field(default=0.0, ge=0)
    imagen_url: str | None = Field(default=None, max_length=255)
    activo: bool = True
    publicado: bool = False
    variantes: list[VarianteIn] | None = None


class ProductoUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    categoria_id: int | None = None
    temporada_id: int | None = None
    proveedor_id: int | None = None
    descripcion: str | None = Field(default=None, max_length=500)
    marca: str | None = Field(default=None, max_length=80)
    genero: str | None = Field(default=None, max_length=30)
    precio_venta: float | None = Field(default=None, ge=0)
    costo: float | None = Field(default=None, ge=0)
    imagen_url: str | None = Field(default=None, max_length=255)
    activo: bool | None = None
    publicado: bool | None = None


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    categoria_id: int
    temporada_id: int | None = None
    proveedor_id: int | None = None
    descripcion: str | None = None
    marca: str | None = None
    genero: str | None = None
    precio_venta: float
    costo: float
    imagen_url: str | None = None
    activo: bool
    publicado: bool
    created_at: datetime
    variantes: list[VarianteOut] = []
