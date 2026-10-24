from sqlalchemy import Boolean, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class Plan(Base):
    """Plan de suscripcion. Global al SaaS, no por tenant."""
    __tablename__ = "planes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))

    max_sucursales: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_usuarios: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_productos: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    modulos: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    precio_mensual: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
