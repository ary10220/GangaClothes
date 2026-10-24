from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base, TenantMixin


class OperacionLog(Base, TenantMixin):
    """Preparado para operacion sin conexion + sincronizacion (CU-18 a CU-23, no implementados este parcial).

    Idempotencia: UNIQUE(tenant_id, uuid_operacion) impide duplicados en reenvios.
    Estados: LOCAL | ENVIADA | CONFIRMADA | RECHAZADA | EN_CONFLICTO.
    """
    __tablename__ = "operaciones_log"
    __table_args__ = (
        UniqueConstraint("tenant_id", "uuid_operacion", name="uq_operacion_tenant_uuid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    uuid_operacion: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="LOCAL")

    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    sincronizado_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
