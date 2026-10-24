from pydantic import AliasChoices, Field, field_validator, model_validator
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
    # Las fotos del seed viven en la web (web/public/img/prendas) y se guardan
    # como ruta relativa ("/img/prendas/x.jpg"): la web las resuelve sola. La app
    # movil necesita la URL completa: definir aqui el dominio de la web
    # (https://ganga-clothes.vercel.app) y el catalogo las devuelve absolutas.
    imagenes_base_url: str = ""
    # Solo para pruebas locales: escribe el codigo en la consola del servidor.
    codigo_recuperacion_en_log: bool = False

    # ------------------------------------------------------------ pasarelas
    # Stripe en modo prueba (CU17). Las claves salen de dashboard.stripe.com
    # con el interruptor "Test mode" encendido: Developers -> API keys.
    # Sin STRIPE_SECRET_KEY el metodo "tarjeta" responde que no esta configurado.
    stripe_secret_key: str = ""
    stripe_public_key: str = ""
    stripe_api_base: str = "https://api.stripe.com/v1"

    # QR del Banco de Credito de Bolivia (OpenBanking). El sandbox exige, ademas
    # de estas credenciales, un certificado de cliente .pfx que el banco entrega
    # aparte; sin el, el host responde 403 antes de mirar el usuario.
    #   BCP_MODO=simulado -> simulador local, util para demostrar sin banco
    #   BCP_MODO=sandbox  -> https://sandbox.openbanking.bcp.com.bo
    #   BCP_MODO=live     -> https://openbanking.bcp.com.bo
    bcp_modo: str = "simulado"
    bcp_usuario: str = ""
    bcp_password: str = ""
    bcp_app_user_id: str = ""
    bcp_public_token: str = ""
    bcp_business_code: str = ""
    bcp_service_code: str = "050"
    # Certificado de cliente para el TLS mutuo que exige el banco. Dos formas,
    # y alcanza con una:
    #   1) el par PEM (.crt + .key) tal como lo entrega el banco;
    #   2) el .pfx con su contrasena, que se convierte a PEM al arrancar.
    # Los archivos viven fuera del control de versiones (.gitignore).
    bcp_cert_pem: str = ""
    bcp_cert_key: str = ""
    bcp_cert_pfx: str = ""
    bcp_cert_password: str = ""
    # Minutos que vive un QR antes de vencer.
    bcp_qr_minutos: int = 15
    # Solo con BCP_MODO=simulado: a los cuantos segundos el simulador da el QR
    # por pagado, como si alguien lo hubiera escaneado. Es lo que hace que la
    # compra con QR se pueda completar sin banco y sin botones de depuracion en
    # la pantalla del cliente. Con 0 el QR queda esperando hasta vencer, que es
    # como se demuestra el desenlace rechazado.
    bcp_simulador_segundos: int = 8

    # ------------------------------------------------------------------- IA
    # Clave de Google AI Studio (aistudio.google.com/apikey), capa gratuita.
    # Se acepta con cualquiera de los tres nombres para no pelear con el .env.
    # SIN clave el chat igual funciona: responde en modo sin modelo, usando las
    # mismas herramientas pero sin redactar (ver ia/service.py).
    gemini_api: str = Field(
        default="",
        validation_alias=AliasChoices("GEMINI_API", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
    )
    # Modelos a probar, en orden, hasta que uno responda. Si Google renombra el
    # de siempre, el siguiente de la lista salva la demo.
    gemini_modelos: str = "gemini-3.8-flash,gemini-3.5-flash-lite,gemini-3-flash-preview,gemini-flash-latest"
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    # Cuantas veces puede el modelo pedir datos antes de tener que responder.
    # Evita que se quede llamando herramientas en circulos.
    ia_max_pasos: int = 4
    # Mensajes de la conversacion que se le recuerdan al modelo.
    ia_memoria_mensajes: int = 12

    @field_validator("bcp_modo")
    @classmethod
    def _modo_conocido(cls, modo: str) -> str:
        modo = (modo or "simulado").strip().lower()
        if modo not in {"simulado", "sandbox", "live"}:
            raise ValueError("BCP_MODO debe ser: simulado, sandbox o live")
        return modo

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
