from pydantic import BaseModel, Field


class CarritoIn(BaseModel):
    """Sucursal desde la que se despacha la compra en linea (opcional)."""

    sucursal_id: int | None = None


class ItemIn(BaseModel):
    variante_id: int
    cantidad: int = Field(default=1, gt=0)


class ItemUpd(BaseModel):
    """Para quitar un item se usa DELETE, no cantidad 0."""

    cantidad: int = Field(gt=0)


class LineaVentaIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0)


class VentaPresencialIn(BaseModel):
    """El cajero sale del token. Con reserva_id y sin detalle, se vende lo reservado;
    con detalle, se vende solo eso (el cliente puede no llevarse todo lo que se probo)."""

    sucursal_id: int
    reserva_id: int | None = None
    detalle: list[LineaVentaIn] | None = None
