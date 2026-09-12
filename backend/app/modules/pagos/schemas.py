from pydantic import BaseModel, Field


class PagoIn(BaseModel):
    venta_id: int
    metodo: str = Field(description="efectivo | tarjeta | qr | pasarela")
    # En efectivo es lo que entrega el cliente (puede haber cambio);
    # con tarjeta, QR o pasarela se cobra el total exacto.
    monto: float = Field(gt=0)
    # Solo para la pasarela en modo prueba: fuerza un rechazo de la tarjeta.
    simular_fallo: bool = False
