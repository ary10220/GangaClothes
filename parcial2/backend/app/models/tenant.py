from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Tenant(Base):
    """Empresa contratante. Es la raiz del multitenancy.
    No hereda TenantMixin: el superadmin es quien la administra.
    """
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    nit: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    correo: Mapped[str] = mapped_column(String(200), nullable=False)
    telefono: Mapped[str | None] = mapped_column(String(50))
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuarios: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    sucursales: Mapped[list["Sucursal"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    suscripciones: Mapped[list["Suscripcion"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
