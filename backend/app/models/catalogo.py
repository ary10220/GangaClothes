from sqlalchemy import (Boolean, Column, Date, ForeignKey, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Categoria(Base):
    __tablename__ = "categoria"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False)
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)


class Temporada(Base):
    __tablename__ = "temporada"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    activo = Column(Boolean, default=True)


class Coleccion(Base):
    __tablename__ = "coleccion"
    id = Column(Integer, primary_key=True)
    temporada_id = Column(Integer, ForeignKey("temporada.id"), nullable=False)
    nombre = Column(String(80), nullable=False)
    anio = Column(Integer)
    descripcion = Column(String(200))


class Talla(Base):
    __tablename__ = "talla"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(10), nullable=False)
    orden = Column(Integer)


class Color(Base):
    __tablename__ = "color"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(40), nullable=False)
    codigo_hex = Column(String(9))


class Prenda(Base):
    __tablename__ = "prenda"
    id = Column(Integer, primary_key=True)
    categoria_id = Column(Integer, ForeignKey("categoria.id"), nullable=False)
    coleccion_id = Column(Integer, ForeignKey("coleccion.id"))
    nombre = Column(String(120), nullable=False)
    descripcion = Column(Text)
    marca = Column(String(80))
    genero = Column(String(20))
    precio_venta = Column(Numeric(10, 2), nullable=False)
    costo = Column(Numeric(10, 2), nullable=False)
    imagen_url = Column(String(255))
    activo = Column(Boolean, default=True)

    variantes = relationship("Variante", back_populates="prenda")


class Variante(Base):
    __tablename__ = "variante"
    __table_args__ = (UniqueConstraint("prenda_id", "talla_id", "color_id"),)
    id = Column(Integer, primary_key=True)
    prenda_id = Column(Integer, ForeignKey("prenda.id"), nullable=False)
    talla_id = Column(Integer, ForeignKey("talla.id"), nullable=False)
    color_id = Column(Integer, ForeignKey("color.id"), nullable=False)
    sku = Column(String(40), nullable=False, unique=True)
    imagen_url = Column(String(255))
    activo = Column(Boolean, default=True)

    prenda = relationship("Prenda", back_populates="variantes")


class AssetAR(Base):
    __tablename__ = "asset_ar"
    id = Column(Integer, primary_key=True)
    variante_id = Column(Integer, ForeignKey("variante.id"), nullable=False)
    tipo = Column(String(20), nullable=False)  # png_overlay | modelo_3d
    url_recurso = Column(String(255), nullable=False)
    escala = Column(Numeric(5, 2), default=1)
