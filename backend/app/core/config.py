from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

SECRETO_DESARROLLO = "solo-para-desarrollo-cambiar"


class Settings(BaseSettings):
    app_name: str = "GangaClothes API"
    # Por defecto SQLite para que cualquiera pueda correr el proyecto sin instalar nada.
    # En produccion (Render) se define DATABASE_URL apuntando a Neon (PostgreSQL).
    database_url: str = "sqlite:///./gangaclothes_dev.db"
    jwt_secret: str = SECRETO_DESARROLLO
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "*"

    @field_validator("database_url")
    @classmethod
    def _esquema_postgresql(cls, url: str) -> str:
        # SQLAlchemy 2 ya no acepta el alias "postgres://" que dan algunos proveedores.
        return "postgresql://" + url[len("postgres://"):] if url.startswith("postgres://") else url

    @model_validator(mode="after")
    def _secreto_real_en_produccion(self):
        # Con el secreto por defecto cualquiera que lea el repo puede firmar tokens.
        if not self.database_url.startswith("sqlite") and self.jwt_secret == SECRETO_DESARROLLO:
            raise ValueError("JWT_SECRET no esta definido: es obligatorio fuera de SQLite local")
        return self

    class Config:
        env_file = ".env"


settings = Settings()
