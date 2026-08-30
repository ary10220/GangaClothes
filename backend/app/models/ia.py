from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        Numeric, String, func)

from app.core.database import Base


class EventoNavegacion(Base):
    __tablename__ = "evento_navegacion"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    prenda_id = Column(Integer, ForeignKey("prenda.id"), nullable=False)
    tipo_evento = Column(String(30), nullable=False)  # vista|busqueda|carrito|probador_ar
    origen = Column(String(10))                       # web | movil
    fecha = Column(DateTime, server_default=func.now())


class Recomendacion(Base):
    __tablename__ = "recomendacion"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    prenda_id = Column(Integer, ForeignKey("prenda.id"), nullable=False)
    motivo = Column(String(200))
    puntaje = Column(Numeric(5, 2))
    fecha = Column(DateTime, server_default=func.now())
    aceptada = Column(Boolean)
