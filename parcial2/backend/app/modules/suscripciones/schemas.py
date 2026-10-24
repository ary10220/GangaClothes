from datetime import date
from pydantic import BaseModel, Field


class ContratarPlanIn(BaseModel):
    plan_codigo: str = Field(min_length=1, max_length=50)
    fecha_inicio: date | None = None
    duracion_dias: int = Field(default=30, ge=1, le=3650)


class PlanOut(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    max_sucursales: int
    max_usuarios: int
    max_productos: int
    modulos: list[str]
    precio_mensual: float
    activo: bool

    class Config:
        from_attributes = True


class SuscripcionOut(BaseModel):
    id: int
    plan: PlanOut
    fecha_inicio: date
    fecha_fin: date | None
    estado: str

    class Config:
        from_attributes = True


class ConsumoLimite(BaseModel):
    recurso: str
    actual: int
    limite: int
    disponible: int

    @classmethod
    def build(cls, recurso: str, actual: int, limite: int) -> "ConsumoLimite":
        return cls(recurso=recurso, actual=actual, limite=limite, disponible=max(0, limite - actual))


class EstadoSuscripcionOut(BaseModel):
    """CU-07: estado y limites del plan vigente con el consumo real."""
    tiene_suscripcion: bool
    plan: PlanOut | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    estado: str | None = None
    consumos: list[ConsumoLimite] = Field(default_factory=list)
    modulos_habilitados: list[str] = Field(default_factory=list)
