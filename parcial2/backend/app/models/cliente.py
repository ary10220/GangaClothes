from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base, TenantMixin


class Cliente(Base, TenantMixin):
    """Cliente del tenant (tienda). CU-11.
    Aislado por tenant_id via TenantMixin.
    Cada empresa maneja su propia cartera de clientes (compradores web, caja, reservas).
    UNIQUE(tenant_id, email) y UNIQUE(tenant_id, ci_nit): unicidad por empresa.
    """
    __tablename__ = "clientes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_clientes_tenant_email"),
        UniqueConstraint("tenant_id", "ci_nit", name="uq_clientes_tenant_ci_nit"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str | None] = mapped_column(String(100))
    ci_nit: Mapped[str | None] = mapped_column(String(30), index=True)
    telefono: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(150), index=True)
    direccion: Mapped[str | None] = mapped_column(String(255))
    ciudad: Mapped[str | None] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, default="regular")  # regular | mayorista | vip
    notas: Mapped[str | None] = mapped_column(String(500))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
