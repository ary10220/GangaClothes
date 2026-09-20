"""Entrada del modulo de envios (CU29).

El cliente NUNCA viaja en el cuerpo: sale del token, igual que en reservas y en
el carrito. El costo tampoco se recibe: lo calcula el backend con `tarifa.py`,
porque si lo mandara la pantalla cualquiera podria pedir envio gratis.
"""
from pydantic import BaseModel, Field


class CotizarIn(BaseModel):
    """Consulta de costo y tiempo. No crea nada: es lo que usa el checkout."""

    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    # Por defecto, la sucursal de despacho del carrito del cliente.
    sucursal_id: int | None = None
    # Por defecto, el total del carrito del cliente (decide el envio gratis).
    monto_compra: float | None = Field(default=None, ge=0)
    express: bool = False


class EnvioIn(BaseModel):
    """Datos de entrega de una compra. Se manda al confirmar, antes de pagar."""

    venta_id: int
    direccion: str = Field(min_length=5, max_length=200)
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    referencia: str | None = Field(default=None, max_length=200)
    telefono_contacto: str = Field(min_length=6, max_length=20)
    express: bool = False


class AsignarIn(BaseModel):
    """A quien se le da el pedido. El repartidor se simula: es un nombre."""

    repartidor: str = Field(min_length=3, max_length=80)


class CancelarIn(BaseModel):
    motivo: str | None = Field(default=None, max_length=200)
