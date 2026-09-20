"""Envio a domicilio de una compra en linea (delivery).

Un envio cuelga de la venta: es la forma en que esa compra llega hasta el
cliente cuando eligio "delivery" en vez de "retiro en sucursal". Una venta
tiene 0..1 envio, y lo impone la clave unica sobre `venta_id`. De que sucursal
sale no se repite aqui: es la de la venta (`venta.sucursal_id`), que es la que
tiene el stock y las coordenadas de origen.

Las coordenadas van en Float y no en Numeric porque no son dinero: se usan para
medir distancias, no para sumar importes. La distancia y el costo si son
Numeric, porque el costo se cobra y tiene que cuadrar al centavo.

El costo y la distancia quedan CONGELADOS al confirmar la compra: si manana
cambia la tarifa, este envio sigue valiendo lo que el cliente acepto.

    pendiente -> asignado -> en_camino -> entregado
        |___________|___________|____> cancelado
"""
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        Numeric, String, func)

from app.core.database import Base


class Envio(Base):
    __tablename__ = "envio"
    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey("venta.id"), nullable=False, unique=True)

    # --- a donde va ---
    # La direccion es texto libre (lo que escribio el cliente); el punto exacto
    # al que llega el repartidor son las coordenadas que marco en el mapa.
    direccion = Column(String(200), nullable=False)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    referencia = Column(String(200))
    telefono_contacto = Column(String(20))

    # --- cuanto costo (ver modules/envios/tarifa.py) ---
    distancia_km = Column(Numeric(6, 2), nullable=False, default=0)
    costo_envio = Column(Numeric(10, 2), nullable=False, default=0)
    express = Column(Boolean, default=False)

    # --- en que anda ---
    estado = Column(String(20), default="pendiente")  # pendiente|asignado|en_camino|entregado|cancelado
    repartidor = Column(String(80))
    motivo_cancelacion = Column(String(200))

    # Cada paso deja su hora: con eso la pantalla de seguimiento arma la linea
    # de tiempo sin tener que inventar fechas.
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_asignacion = Column(DateTime)
    fecha_salida = Column(DateTime)
    fecha_estimada = Column(DateTime)
    fecha_entrega = Column(DateTime)
