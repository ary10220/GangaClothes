from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base, TenantMixin


class Suscripcion(Base, TenantMixin):
    """Contratacion de un plan por parte de un tenant.
    Hereda TenantMixin: el filtro central restringe que un tenant vea su suscripcion.
    """
    __tablename__ = "suscripciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("planes.id"), nullable=False)

    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date)

    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
    """activa | suspendida | vencida | cancelada"""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="suscripciones")
    plan: Mapped["Plan"] = relationship()
