from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.core.database import Base


class Ciudad(Base):
    __tablename__ = "ciudad"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False)
    departamento = Column(String(80))


class Sucursal(Base):
    __tablename__ = "sucursal"
    id = Column(Integer, primary_key=True)
    ciudad_id = Column(Integer, ForeignKey("ciudad.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(200))
    telefono = Column(String(20))
    horario = Column(String(100))
    activo = Column(Boolean, default=True)
