from datetime import datetime
from pydantic import BaseModel, Field


class SucursalIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    nombre: str = Field(min_length=1, max_length=200)
    ciudad: str = Field(min_length=1, max_length=100)
    direccion: str = Field(min_length=1, max_length=300)
    horario: str | None = None


class SucursalUpdateIn(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    ciudad: str | None = Field(default=None, min_length=1, max_length=100)
    direccion: str | None = Field(default=None, min_length=1, max_length=300)
    horario: str | None = None
    estado: str | None = None
    activo: bool | None = None


class SucursalOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    ciudad: str
    direccion: str
    horario: str | None
    estado: str
    activo: bool
    created_at: datetime | None = None

    class Config:
        from_attributes = True
