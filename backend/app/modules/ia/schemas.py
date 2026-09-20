from pydantic import BaseModel, Field


class ChatIn(BaseModel):
    mensaje: str = Field(min_length=1, max_length=1000)
    # Sin conversacion_id se abre un hilo nuevo; con el, se sigue el anterior
    # (es lo que le da memoria al asistente).
    conversacion_id: int | None = None
    origen: str | None = Field(default=None, pattern="^(web|movil)$")
    # Si la pantalla ya tiene elegida una sucursal, el asistente solo ofrece lo
    # que hay ahi. Sin esto, mira el stock de toda la tienda.
    sucursal_id: int | None = None


class EventoIn(BaseModel):
    """CU28: lo que el cliente mira. Alimenta el recomendador."""

    prenda_id: int
    tipo_evento: str = Field(default="vista", pattern="^(vista|busqueda|carrito|probador_ar)$")
    origen: str | None = Field(default=None, pattern="^(web|movil)$")
