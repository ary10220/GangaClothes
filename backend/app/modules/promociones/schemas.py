from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PromocionIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=200)
    tipo_descuento: Literal["porcentaje", "monto"]
    valor: float = Field(gt=0)
    fecha_inicio: date
    fecha_fin: date
    activo: bool = True
    # Prendas a las que se aplica. Se reemplaza la lista completa en cada guardado.
    prenda_ids: list[int] = []


class PromocionUpd(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=200)
    tipo_descuento: Literal["porcentaje", "monto"] | None = None
    valor: float | None = Field(default=None, gt=0)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    activo: bool | None = None
    prenda_ids: list[int] | None = None
