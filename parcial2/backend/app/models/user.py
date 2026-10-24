from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base, TenantMixin


class User(Base, TenantMixin):
    """Usuario perteneciente a un tenant.
    - UNIQUE(tenant_id, email): el mismo correo puede existir en dos empresas distintas.
    - El superadministrador vive en otra tabla (SuperAdmin), fuera del aislamiento por tenant.
    """
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    email: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[str] = mapped_column(String(50), nullable=False, default="admin")
    """admin | encargado | cajero | ..."""
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="usuarios")
