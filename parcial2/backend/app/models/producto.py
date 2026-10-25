from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base, TenantMixin


class Producto(Base, TenantMixin):
    """Producto o prenda del catalogo. CU-08.
    Aislado por tenant_id via TenantMixin.
    UNIQUE(tenant_id, nombre): cada empresa maneja su propio catalogo de productos.
    """
    __tablename__ = "productos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_productos_tenant_nombre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    categoria_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categorias.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    temporada_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("temporadas.id", ondelete="SET NULL"), index=True
    )
    proveedor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("proveedores.id", ondelete="SET NULL"), index=True
    )

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500))
    marca: Mapped[str | None] = mapped_column(String(80))
    genero: Mapped[str | None] = mapped_column(String(30))  # unisex | hombre | mujer | ninos
    precio_venta: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    costo: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    imagen_url: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    publicado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    categoria = relationship("Categoria")
    temporada = relationship("Temporada")
    proveedor = relationship("Proveedor")
    variantes: Mapped[list["Variante"]] = relationship(
        back_populates="producto", cascade="all, delete-orphan", order_by="Variante.id"
    )


class Variante(Base, TenantMixin):
    """Variante especifica de un producto (combinacion de Talla y Color con su SKU). CU-08.
    UNIQUE(tenant_id, sku): el codigo de barras o SKU es unico por empresa.
    UNIQUE(producto_id, talla_id, color_id): no puede haber dos variantes identicas para el mismo producto.
    """
    __tablename__ = "variantes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_variantes_tenant_sku"),
        UniqueConstraint("producto_id", "talla_id", "color_id", name="uq_variantes_prod_talla_color"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    producto_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("productos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    talla_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tallas.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    color_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("colores.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    sku: Mapped[str] = mapped_column(String(60), nullable=False)
    precio_adicional: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0.0)
    imagen_url: Mapped[str | None] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    producto: Mapped["Producto"] = relationship(back_populates="variantes")
    talla = relationship("Talla")
    color = relationship("Color")
