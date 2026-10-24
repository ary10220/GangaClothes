from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GangaSaaS Parcial2"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./ganga_saas.db"

    jwt_secret: str = "cambia-esto-en-produccion-por-un-secret-largo-y-aleatorio"
    jwt_alg: str = "HS256"
    jwt_exp_minutes: int = 60 * 8

    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
