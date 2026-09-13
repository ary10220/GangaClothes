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

    # Correo saliente para recuperar la contrasena. Con Gmail, SMTP_PASSWORD es
    # una contrasena de aplicacion (myaccount.google.com/apppasswords).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_usuario: str = ""
    smtp_password: str = ""
    smtp_nombre_remitente: str = "GangaClothes"
    # En Render (plan gratuito sin SMTP) el correo sale por la API HTTPS de Brevo.
    brevo_api_key: str = ""
    # Direccion que figura como remitente; por defecto SMTP_USUARIO. En Brevo
    # tiene que estar verificada como remitente.
    correo_remitente: str = ""
    # Solo para pruebas locales: escribe el codigo en la consola del servidor.
    codigo_recuperacion_en_log: bool = False

    @field_validator("smtp_password")
    @classmethod
    def _sin_espacios(cls, clave: str) -> str:
        # Google la muestra en grupos de 4 ("abcd efgh ..."); los espacios no son parte.
        return clave.replace(" ", "")

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
