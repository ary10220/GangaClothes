from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        Numeric, String, Text, func)

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


class Conversacion(Base):
    """Un hilo de chat con el asistente (CU28).

    Cuelga del usuario y no del cliente porque el mismo asistente atiende al
    personal: un administrador conversa sobre reportes y no tiene ficha de
    cliente.
    """

    __tablename__ = "conversacion"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    titulo = Column(String(120))
    # web | movil, para saber desde donde se conversa.
    origen = Column(String(10))
    creada = Column(DateTime, server_default=func.now())
    actualizada = Column(DateTime, server_default=func.now())
    activa = Column(Boolean, default=True)


class MensajeChat(Base):
    """Cada turno del hilo, en el orden en que ocurrio.

    `rol` sigue el vocabulario del modelo: "usuario" lo que escribio la persona,
    "asistente" lo que respondio, y "herramienta" el registro de una consulta a
    nuestra propia API (que prendas devolvio una busqueda, que dio un reporte).
    Ese tercer tipo no se muestra en pantalla: esta para poder auditar de donde
    salio cada dato que el asistente dijo.
    """

    __tablename__ = "mensaje_chat"
    id = Column(Integer, primary_key=True)
    conversacion_id = Column(Integer, ForeignKey("conversacion.id"), nullable=False)
    rol = Column(String(15), nullable=False)      # usuario | asistente | herramienta
    texto = Column(Text)
    # Solo en las filas de rol "herramienta".
    herramienta = Column(String(40))
    argumentos = Column(Text)                     # JSON de lo que se le pidio
    fecha = Column(DateTime, server_default=func.now())
