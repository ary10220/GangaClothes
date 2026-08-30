from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        Numeric, String, UniqueConstraint, func)

from app.core.database import Base


class Inventario(Base):
    __tablename__ = "inventario"
    __table_args__ = (UniqueConstraint("variante_id", "sucursal_id"),)
    id = Column(Integer, primary_key=True)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=0)
    cantidad_reservada = Column(Integer, nullable=False, default=0)
    stock_minimo = Column(Integer, default=0)
    stock_maximo = Column(Integer, default=0)


class MovimientoInventario(Base):
    __tablename__ = "movimiento_inventario"
    id = Column(Integer, primary_key=True)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    tipo = Column(String(20), nullable=False)  # ingreso | salida | ajuste | devolucion
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(200))
    fecha = Column(DateTime, server_default=func.now())


class Proveedor(Base):
    __tablename__ = "proveedor"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    nit = Column(String(20))
    contacto = Column(String(100))
    telefono = Column(String(20))
    email = Column(String(120))
    direccion = Column(String(200))
    activo = Column(Boolean, default=True)


class Compra(Base):
    __tablename__ = "compra"
    id = Column(Integer, primary_key=True)
    proveedor_id = Column(Integer, ForeignKey("proveedor.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursal.id"), nullable=False)
    fecha = Column(DateTime, server_default=func.now())
    estado = Column(String(20), default="pendiente")  # pendiente | recibida | anulada
    total = Column(Numeric(12, 2), default=0)


class DetalleCompra(Base):
    __tablename__ = "detalle_compra"
    id = Column(Integer, primary_key=True)
    compra_id = Column(Integer, ForeignKey("compra.id"), nullable=False)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
