"""Envio de correos por SMTP (Gmail con contrasena de aplicacion).

Las credenciales salen de variables de entorno (SMTP_USUARIO, SMTP_PASSWORD):
en local desde backend/.env y en Render desde sus variables. Nunca del codigo.
"""
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings


def configurado() -> bool:
    return bool(settings.smtp_usuario and settings.smtp_password)


def enviar(destinatario: str, asunto: str, texto: str, html: str | None = None) -> None:
    """Envia un correo. Lanza la excepcion de smtplib si falla: quien llama decide."""
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = formataddr((settings.smtp_nombre_remitente, settings.smtp_usuario))
    mensaje["To"] = destinatario
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")

    contexto = ssl.create_default_context()
    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=contexto, timeout=20) as smtp:
            smtp.login(settings.smtp_usuario, settings.smtp_password)
            smtp.send_message(mensaje)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls(context=contexto)
            smtp.login(settings.smtp_usuario, settings.smtp_password)
            smtp.send_message(mensaje)
