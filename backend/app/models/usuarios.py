from sqlalchemy import (Boolean, Column, Date, DateTime, ForeignKey, Integer,
                        String, UniqueConstraint, func)

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuario"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100))
    email = Column(String(120), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    telefono = Column(String(20))
    activo = Column(Boolean, default=True)
    ultimo_acceso = Column(DateTime)
    fecha_registro = Column(DateTime, server_default=func.now())


class Rol(Base):
    __tablename__ = "rol"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False, unique=True)
    descripcion = Column(String(200))
    activo = Column(Boolean, default=True)


class UsuarioRol(Base):
    __tablename__ = "usuario_rol"
    __table_args__ = (UniqueConstraint("usuario_id", "rol_id"),)
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False)
    rol_id = Column(Integer, ForeignKey("rol.id"), nullable=False)
    fecha_asignacion = Column(DateTime, server_default=func.now())


class Cliente(Base):
    __tablename__ = "cliente"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, unique=True)
    nit_ci = Column(String(20))
    direccion = Column(String(200))
    fecha_nacimiento = Column(Date)
    genero = Column(String(20))
    talla_preferida = Column(String(10))
