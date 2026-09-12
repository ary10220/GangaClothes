from pydantic import BaseModel, Field


class InventarioIn(BaseModel):
    """Alta del registro de stock de una variante en una sucursal."""

    variante_id: int
    sucursal_id: int
    cantidad: int = Field(default=0, ge=0)
    stock_minimo: int = Field(default=0, ge=0)
    stock_maximo: int = Field(default=0, ge=0)


class LimitesUpd(BaseModel):
    """Solo se editan los limites: la cantidad se mueve con un movimiento."""

    stock_minimo: int | None = Field(default=None, ge=0)
    stock_maximo: int | None = Field(default=None, ge=0)


class MovimientoIn(BaseModel):
    tipo: str = Field(description="ingreso | salida | ajuste | devolucion")
    variante_id: int
    sucursal_id: int
    # En un ajuste la cantidad es el total contado, no lo que entra o sale.
    cantidad: int = Field(ge=0)
    motivo: str | None = Field(default=None, max_length=200)


class LineaCompraIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0)


class CompraIn(BaseModel):
    proveedor_id: int
    sucursal_id: int
    detalle: list[LineaCompraIn]
