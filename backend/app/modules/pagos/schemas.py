from pydantic import BaseModel, Field


class PagoIn(BaseModel):
    venta_id: int
    metodo: str = Field(description="efectivo | tarjeta | qr  ('pasarela' se acepta como sinonimo de tarjeta)")
    # En efectivo es lo que entrega el cliente (puede haber cambio);
    # con tarjeta o QR se cobra el total exacto.
    monto: float = Field(gt=0)
    # Tarjeta en linea: el numero elige la tarjeta de prueba de Stripe. No se
    # guarda en ningun lado ni se manda a la pasarela tal cual (ver stripe_gw).
    numero_tarjeta: str | None = Field(default=None, max_length=25)


class QrIn(BaseModel):
    venta_id: int


class QrSimularIn(BaseModel):
    qr_id: str
    # Opcional: el QR ya identifica su venta, asi que quien llama no tiene por
    # que saberla. Se acepta igual para poder verificar que coincidan.
    venta_id: int | None = None
    # C = en cola, P = procesado (pagado), V = vencido, A = anulado
    estado: str = Field(default="P", pattern="^[CPVAU]$")
