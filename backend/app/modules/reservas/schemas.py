from datetime import datetime

from pydantic import BaseModel, Field


class LineaReservaIn(BaseModel):
    variante_id: int
    cantidad: int = Field(default=1, gt=0)


class ReservaIn(BaseModel):
    """El cliente NO viaja en el body: sale del token."""

    sucursal_id: int
    fecha_hora_prueba: datetime
    notas: str | None = Field(default=None, max_length=200)
    detalle: list[LineaReservaIn]
