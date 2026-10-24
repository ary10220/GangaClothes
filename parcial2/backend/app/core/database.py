from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from sqlalchemy import ForeignKey, Integer, create_engine, event
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    declared_attr,
    mapped_column,
    sessionmaker,
    with_loader_criteria,
)

from .config import get_settings


settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TenantMixin:
    """Marcador para modelos aislados por tenant. Aporta `tenant_id` via `declared_attr`
    para que `with_loader_criteria(TenantMixin, ...)` pueda referenciarlo sin que cada
    modelo tenga que redeclararlo. El filtro se aplica en `_apply_tenant_filter` abajo.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[int]:
        return mapped_column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )


@dataclass
class TenantScope:
    user_id: int | None = None
    tenant_id: int | None = None
    roles: list[str] = field(default_factory=list)
    is_super: bool = False

    @property
    def has_tenant(self) -> bool:
        return self.tenant_id is not None


@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(execute_state):
    """
    Aislamiento multitenant CENTRAL.
    Cualquier SELECT sobre un modelo que hereda `TenantMixin` queda filtrado
    automaticamente por el `tenant_id` del scope guardado en `session.info["tenant_scope"]`.
    Olvidarse del filtro es imposible por diseno: el filtro no se aplica en el servicio,
    se aplica en la ejecucion del ORM.

    - Usuario de tenant: solo ve filas de su tenant.
    - Superadmin: puede ver todo (no se aplica criterio).
    - Sin scope (startup, seeds): no se filtra. Ver `scoped_session_ctx` para scope temporal.
    """
    if not (execute_state.is_select or execute_state.is_update or execute_state.is_delete):
        return
    if execute_state.is_relationship_load:
        return

    scope: TenantScope | None = execute_state.session.info.get("tenant_scope")
    if scope is None or scope.is_super:
        return
    if scope.tenant_id is None:
        return

    tid = scope.tenant_id
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantMixin,
            lambda cls: cls.tenant_id == tid,
            include_aliases=True,
            track_closure_variables=False,
        )
    )


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def attach_scope(db: Session, scope: TenantScope) -> None:
    """Guarda el scope en la sesion para que el listener lo aplique."""
    db.info["tenant_scope"] = scope


def init_db() -> None:
    """Crea tablas si no existen. Importa aqui para registrar modelos."""
    from ..models import tenant, plan, suscripcion, user, superadmin, sucursal, operacion  # noqa: F401

    Base.metadata.create_all(bind=engine)
