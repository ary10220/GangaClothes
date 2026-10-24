from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base, TenantMixin


class Sucursal(Base, TenantMixin):
    """Sucursal del tenant. CU-04.
    UNIQUE(tenant_id, codigo): dos empresas pueden tener su propia 'suc-01' sin chocar.
    """
    __tablename__ = "sucursales"
    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_sucursales_tenant_codigo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
    direccion: Mapped[str] = mapped_column(String(300), nullable=False)
    horario: Mapped[str | None] = mapped_column(String(200))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="sucursales")
