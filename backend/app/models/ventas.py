from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer,
                        Numeric, String, UniqueConstraint, func)

from app.core.database import Base


class Reserva(Base):
    __tablename__ = "reserva"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_hora_prueba = Column(DateTime, nullable=False)
    estado = Column(String(20), default="pendiente")  # pendiente|preparada|atendida|cancelada|expirada
    notas = Column(String(200))


class DetalleReserva(Base):
    __tablename__ = "detalle_reserva"
    id = Column(Integer, primary_key=True)
    reserva_id = Column(Integer, ForeignKey("reserva.id"), nullable=False)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    estado = Column(String(20), default="reservado")


class Venta(Base):
    __tablename__ = "venta"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("cliente.id"))
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    cajero_id = Column(Integer, ForeignKey("usuario.id"))      # solo canal caja (0..1)
    reserva_id = Column(Integer, ForeignKey("reserva.id"))     # venta originada en reserva (0..1)
    canal = Column(String(10), nullable=False)                 # web | movil | caja
    fecha = Column(DateTime, server_default=func.now())
    estado = Column(String(20), default="carrito")             # carrito|pendiente|pagada|anulada
    subtotal = Column(Numeric(12, 2), default=0)
    descuento = Column(Numeric(12, 2), default=0)
    total = Column(Numeric(12, 2), default=0)
    nro_comprobante = Column(String(30))


class DetalleVenta(Base):
    __tablename__ = "detalle_venta"
    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey("venta.id"), nullable=False)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    descuento = Column(Numeric(10, 2), default=0)
    subtotal = Column(Numeric(12, 2), nullable=False)


class Pago(Base):
    __tablename__ = "pago"
    id = Column(Integer, primary_key=True)
    venta_id = Column(Integer, ForeignKey("venta.id"), nullable=False)
    metodo = Column(String(20), nullable=False)  # efectivo | tarjeta | qr | pasarela
    pasarela = Column(String(30))                # stripe
    monto = Column(Numeric(12, 2), nullable=False)
    moneda = Column(String(5), default="BOB")
    estado = Column(String(20), default="pendiente")  # pendiente | exitoso | fallido
    referencia_externa = Column(String(80))
    fecha = Column(DateTime, server_default=func.now())


class Promocion(Base):
    __tablename__ = "promocion"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(200))
    tipo_descuento = Column(String(15), nullable=False)  # porcentaje | monto
    valor = Column(Numeric(10, 2), nullable=False)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    activo = Column(Boolean, default=True)


class PromocionPrenda(Base):
    __tablename__ = "promocion_prenda"
    __table_args__ = (UniqueConstraint("promocion_id", "prenda_id"),)
    id = Column(Integer, primary_key=True)
    promocion_id = Column(Integer, ForeignKey("promocion.id"), nullable=False)
    prenda_id = Column(Integer, ForeignKey("prenda.id"), nullable=False)
