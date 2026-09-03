from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

if settings.database_url.startswith("sqlite"):
    # SQLite ignora las claves foraneas salvo que se pidan en cada conexion.
    # Sin esto, en local se borrarian filas que PostgreSQL (Neon) rechazaria,
    # y nunca se ejecutaria el "desactivar en lugar de eliminar" de comunes.py.
    @event.listens_for(engine, "connect")
    def _activar_claves_foraneas(conexion, _registro):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def to_dict(obj):
    """Convierte una fila SQLAlchemy en dict serializable."""
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
