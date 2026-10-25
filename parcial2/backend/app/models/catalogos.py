from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base, TenantMixin


class Categoria(Base, TenantMixin):
    """Categoria de prenda (ej: Poleras, Pantalones, Vestidos). CU-09.
    UNIQUE(tenant_id, nombre): cada empresa maneja su propio catalogo de categorias.
    """
    __tablename__ = "categorias"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_categorias_tenant_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Talla(Base, TenantMixin):
    """Talla para prendas (ej: S, M, L, XL, 38, 40). CU-09.
    UNIQUE(tenant_id, nombre): tallas independientes por tenant.
    """
    __tablename__ = "tallas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_tallas_tenant_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Color(Base, TenantMixin):
    """Color para prendas (ej: Rojo, Negro, Blanco). CU-09.
    UNIQUE(tenant_id, nombre): colores independientes por tenant.
    """
    __tablename__ = "colores"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_colores_tenant_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    codigo_hex: Mapped[str | None] = mapped_column(String(10))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Temporada(Base, TenantMixin):
    """Temporada comercial (ej: Verano 2026, Invierno 2026). CU-09.
    UNIQUE(tenant_id, nombre): temporadas independientes por tenant.
    """
    __tablename__ = "temporadas"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_temporadas_tenant_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    fecha_inicio: Mapped[date | None] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
