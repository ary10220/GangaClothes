from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "GangaClothes API"
    # Por defecto SQLite para que cualquiera pueda correr el proyecto sin instalar nada.
    # En produccion (Render) se define DATABASE_URL apuntando a Neon (PostgreSQL).
    database_url: str = "sqlite:///./gangaclothes_dev.db"
    jwt_secret: str = "solo-para-desarrollo-cambiar"
    jwt_alg: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "*"

    class Config:
        env_file = ".env"


settings = Settings()
