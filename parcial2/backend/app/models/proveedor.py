from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base, TenantMixin


class Proveedor(Base, TenantMixin):
    """Proveedor de prendas y suministros. CU-10.
    UNIQUE(tenant_id, nombre): cada empresa gestiona su propia cartera de proveedores.
    """
    __tablename__ = "proveedores"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_proveedores_tenant_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    nit: Mapped[str | None] = mapped_column(String(50))
    contacto: Mapped[str | None] = mapped_column(String(100))
    telefono: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(150))
    direccion: Mapped[str | None] = mapped_column(String(255))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
