"""Envio de correos.

Dos caminos, segun la configuracion:

- BREVO_API_KEY definida: API HTTPS de Brevo (puerto 443). Es la que se usa en
  Render, porque el plan gratuito bloquea la salida por SMTP (465/587).
- Si no: SMTP (Gmail con contrasena de aplicacion). Sirve en local.

Las credenciales salen de variables de entorno, nunca del codigo.
"""
import json
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def remitente() -> str:
    return settings.correo_remitente or settings.smtp_usuario


def proveedor() -> str | None:
    if settings.brevo_api_key and remitente():
        return "brevo"
    if settings.smtp_usuario and settings.smtp_password:
        return "smtp"
    return None


def configurado() -> bool:
    return proveedor() is not None


def enviar(destinatario: str, asunto: str, texto: str, html: str | None = None) -> str:
    """Envia un correo y devuelve el proveedor usado. Si falla, lanza la excepcion."""
    via = proveedor()
    if via == "brevo":
        _por_brevo(destinatario, asunto, texto, html)
    elif via == "smtp":
        _por_smtp(destinatario, asunto, texto, html)
    else:
        raise RuntimeError("No hay proveedor de correo configurado (BREVO_API_KEY o SMTP_USUARIO/SMTP_PASSWORD)")
    return via


def _por_brevo(destinatario: str, asunto: str, texto: str, html: str | None) -> None:
    cuerpo = {
        "sender": {"name": settings.smtp_nombre_remitente, "email": remitente()},
        "to": [{"email": destinatario}],
        "subject": asunto,
        "textContent": texto,
    }
    if html:
        cuerpo["htmlContent"] = html
    peticion = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(cuerpo).encode("utf-8"),
        method="POST",
        headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            if respuesta.status not in (200, 201, 202):
                raise RuntimeError(f"Brevo respondio {respuesta.status}")
    except urllib.error.HTTPError as error:
        # Brevo explica el motivo (clave invalida, remitente sin verificar...): se deja en el log.
        detalle = error.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"Brevo rechazo el envio ({error.code}): {detalle}") from None


def _por_smtp(destinatario: str, asunto: str, texto: str, html: str | None) -> None:
    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = formataddr((settings.smtp_nombre_remitente, remitente()))
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
