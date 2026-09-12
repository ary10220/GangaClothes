"""Permisos por rol y bitacora de acciones (CU3 y seguridad del sistema).

Un permiso es la combinacion de un modulo del sistema con una accion sobre el
(por ejemplo PRENDAS + CREAR). Los roles agrupan permisos, y los usuarios
reciben roles: asi el acceso se administra por rol y no usuario por usuario.
"""
from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String,
                        UniqueConstraint, func)

from app.core.database import Base


class Permiso(Base):
    __tablename__ = "permiso"
    id = Column(Integer, primary_key=True)
    # codigo es lo que se valida en el backend: "prendas:crear"
    codigo = Column(String(60), nullable=False, unique=True, index=True)
    modulo = Column(String(40), nullable=False, index=True)
    accion = Column(String(20), nullable=False)
    nombre = Column(String(80), nullable=False)
    descripcion = Column(String(200))


class RolPermiso(Base):
    __tablename__ = "rol_permiso"
    __table_args__ = (UniqueConstraint("rol_id", "permiso_id"),)
    id = Column(Integer, primary_key=True)
    rol_id = Column(Integer, ForeignKey("rol.id"), nullable=False, index=True)
    permiso_id = Column(Integer, ForeignKey("permiso.id"), nullable=False, index=True)


class Bitacora(Base):
    """Una fila por accion registrada. Nunca se edita ni se borra."""

    __tablename__ = "bitacora"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, server_default=func.now(), index=True)
    # El usuario puede llegar a borrarse; el texto del actor queda igual.
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    actor = Column(String(160), nullable=False)
    modulo = Column(String(40), nullable=False, index=True)
    accion = Column(String(20), nullable=False, index=True)
    nivel = Column(String(10), nullable=False, default="INFO")
    entidad = Column(String(60))
    entidad_id = Column(Integer)
    detalle = Column(String(400))
    ip = Column(String(45))
