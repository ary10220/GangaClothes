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
    # Cuenta con la que el proveedor entra a su portal (CU9). Una por proveedor.
    usuario_id = Column(Integer, ForeignKey("usuario.id"), unique=True)


class ProductoProveedor(Base):
    """CU9: un producto que el proveedor informa que puede vender, con su precio
    referencial. No es una prenda de la tienda: es la oferta que el encargado
    consulta al armar una compra."""

    __tablename__ = "producto_proveedor"
    id = Column(Integer, primary_key=True)
    proveedor_id = Column(Integer, ForeignKey("proveedor.id"), nullable=False, index=True)
    categoria_id = Column(Integer, ForeignKey("categoria.id"))
    # Prenda del catalogo de la tienda a la que corresponde este producto (0..1).
    # La define el personal de la tienda, no el proveedor: al comprar, acota las
    # variantes destino a las de esa prenda.
    prenda_id = Column(Integer, ForeignKey("prenda.id"))
    nombre = Column(String(120), nullable=False)
    descripcion = Column(String(300))
    precio_referencial = Column(Numeric(10, 2), nullable=False)
    cantidad_minima = Column(Integer, default=1)
    disponible = Column(Boolean, default=True)
    fecha_actualizacion = Column(DateTime, server_default=func.now())


class ProductoProveedorTemporada(Base):
    __tablename__ = "producto_proveedor_temporada"
    __table_args__ = (UniqueConstraint("producto_id", "temporada_id"),)
    id = Column(Integer, primary_key=True)
    producto_id = Column(Integer, ForeignKey("producto_proveedor.id"), nullable=False, index=True)
    temporada_id = Column(Integer, ForeignKey("temporada.id"), nullable=False)


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
    # Producto de la oferta del proveedor del que partio la linea (0..1: queda
    # vacio si el proveedor no tenia oferta cargada al armar la compra).
    producto_proveedor_id = Column(Integer, ForeignKey("producto_proveedor.id"))
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
