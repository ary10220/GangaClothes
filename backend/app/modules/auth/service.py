import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import correo
from app.core.config import settings
from app.core.contrasenas import exigir_segura
from app.core.security import hash_password, verify_password
from app.models.seguridad import RecuperacionContrasena
from app.models.usuarios import Cliente, Rol, Usuario, UsuarioRol

log = logging.getLogger("gangaclothes.auth")

# Recuperacion de contrasena
MINUTOS_CODIGO = 15
MAX_INTENTOS = 5
SEGUNDOS_ENTRE_ENVIOS = 60


def obtener_roles(db: Session, usuario_id: int) -> list[str]:
    filas = (
        db.query(Rol.nombre)
        .join(UsuarioRol, UsuarioRol.rol_id == Rol.id)
        .filter(UsuarioRol.usuario_id == usuario_id)
        .all()
    )
    return [r[0] for r in filas]


def asignar_rol(db: Session, usuario_id: int, nombre_rol: str) -> None:
    rol = db.query(Rol).filter(Rol.nombre == nombre_rol).first()
    if rol is None:
        rol = Rol(nombre=nombre_rol)
        db.add(rol)
        db.flush()
    existe = (
        db.query(UsuarioRol)
        .filter(UsuarioRol.usuario_id == usuario_id, UsuarioRol.rol_id == rol.id)
        .first()
    )
    if existe is None:
        db.add(UsuarioRol(usuario_id=usuario_id, rol_id=rol.id))


def _por_email(db: Session, email: str) -> Usuario | None:
    # El correo no distingue mayusculas: Maria@x.com y maria@x.com son la misma cuenta.
    return db.query(Usuario).filter(func.lower(Usuario.email) == email.strip().lower()).first()


def registrar_cliente(db: Session, datos) -> Usuario:
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(400, "El nombre es obligatorio")
    exigir_segura(datos.password)
    if _por_email(db, datos.email):
        raise HTTPException(400, "Ya existe una cuenta con ese correo. Inicia sesion o usa otro correo")

    usuario = Usuario(
        nombre=nombre,
        apellido=(datos.apellido or "").strip() or None,
        email=datos.email.strip().lower(),
        password_hash=hash_password(datos.password),
        telefono=(datos.telefono or "").strip() or None,
    )
    db.add(usuario)
    try:
        db.flush()
        db.add(Cliente(usuario_id=usuario.id))
        asignar_rol(db, usuario.id, "cliente")
        db.commit()
    except IntegrityError:
        # Dos registros simultaneos con el mismo correo: la base deja pasar a uno.
        db.rollback()
        raise HTTPException(400, "Ya existe una cuenta con ese correo. Inicia sesion o usa otro correo")
    db.refresh(usuario)
    return usuario


def autenticar(db: Session, email: str, password: str) -> Usuario:
    usuario = _por_email(db, email)
    if usuario is None or not verify_password(password, usuario.password_hash):
        raise HTTPException(401, "Correo o contrasena incorrectos")
    if not usuario.activo:
        raise HTTPException(401, "Usuario inactivo")
    usuario.ultimo_acceso = datetime.utcnow()
    db.commit()
    return usuario


# ------------------------------------------------- recuperar contrasena
def _hash_codigo(usuario_id: int, codigo: str) -> str:
    # HMAC con el secreto del servidor: sin el secreto, la tabla no sirve para
    # probar los 10^6 codigos posibles.
    return hmac.new(settings.jwt_secret.encode(), f"{usuario_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def solicitar_recuperacion(db: Session, email: str) -> tuple[Usuario, str] | None:
    """Genera un codigo nuevo. Devuelve None si no corresponde enviar nada.

    Quien llama responde lo mismo en ambos casos: asi nadie puede averiguar
    que correos tienen cuenta.
    """
    usuario = _por_email(db, email)
    if usuario is None or usuario.activo is False:
        return None

    ahora = datetime.utcnow()
    ultimo = (
        db.query(RecuperacionContrasena)
        .filter(RecuperacionContrasena.usuario_id == usuario.id)
        .order_by(RecuperacionContrasena.id.desc())
        .first()
    )
    # Un envio por minuto: evita llenar el correo de alguien pidiendo codigos.
    if ultimo and not ultimo.usado and ultimo.fecha > ahora - timedelta(seconds=SEGUNDOS_ENTRE_ENVIOS):
        return None

    # Pedir uno nuevo invalida los anteriores.
    db.execute(
        update(RecuperacionContrasena)
        .where(RecuperacionContrasena.usuario_id == usuario.id, RecuperacionContrasena.usado == False)  # noqa: E712
        .values(usado=True)
    )
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    db.add(RecuperacionContrasena(
        usuario_id=usuario.id, codigo_hash=_hash_codigo(usuario.id, codigo), fecha=ahora,
        expira=ahora + timedelta(minutes=MINUTOS_CODIGO), intentos=0, usado=False,
    ))
    db.commit()
    return usuario, codigo


def enviar_codigo(email: str, nombre: str, codigo: str) -> None:
    """Se ejecuta despues de responder (BackgroundTasks). Nunca lanza: registra el error."""
    if settings.codigo_recuperacion_en_log:
        log.warning("Codigo de recuperacion para %s: %s", email, codigo)
    if not correo.configurado():
        log.error("Correo sin configurar (BREVO_API_KEY o SMTP_USUARIO/SMTP_PASSWORD): no se envio el codigo a %s", email)
        return

    texto = (
        f"Hola {nombre}:\n\n"
        f"Tu codigo para crear una contrasena nueva en GangaClothes es: {codigo}\n\n"
        f"Vence en {MINUTOS_CODIGO} minutos y sirve una sola vez.\n"
        "Si no pediste cambiar tu contrasena, ignora este correo: tu cuenta sigue igual.\n"
    )
    html = f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:460px;margin:auto;color:#14161a">
  <div style="font-weight:900;font-size:22px;letter-spacing:-.5px">GANGA<span style="color:#e8175d">CLOTHES</span></div>
  <p>Hola {nombre}:</p>
  <p>Usa este codigo para crear una contrasena nueva:</p>
  <div style="font-family:Consolas,monospace;font-size:34px;font-weight:700;letter-spacing:10px;
              background:#f2f2ed;border:2px solid #14161a;border-radius:12px;padding:14px;text-align:center">{codigo}</div>
  <p style="color:#6b6f76;font-size:13px">Vence en {MINUTOS_CODIGO} minutos y sirve una sola vez.<br>
  Si no pediste cambiar tu contrasena, ignora este correo: tu cuenta sigue igual.</p>
</div>"""
    try:
        via = correo.enviar(email, f"Tu codigo de GangaClothes: {codigo}", texto, html)
        log.info("Codigo de recuperacion enviado a %s (via %s)", email, via)
    except Exception:
        log.exception("No se pudo enviar el codigo de recuperacion a %s", email)


def restablecer_contrasena(db: Session, email: str, codigo: str, password: str) -> Usuario:
    exigir_segura(password)
    invalido = HTTPException(400, "El codigo es incorrecto o ya vencio. Revisa el correo o pide uno nuevo")

    usuario = _por_email(db, email)
    if usuario is None or usuario.activo is False:
        raise invalido
    registro = (
        db.query(RecuperacionContrasena)
        .filter(RecuperacionContrasena.usuario_id == usuario.id, RecuperacionContrasena.usado == False)  # noqa: E712
        .order_by(RecuperacionContrasena.id.desc())
        .first()
    )
    if registro is None or registro.expira <= datetime.utcnow():
        raise invalido
    if registro.intentos >= MAX_INTENTOS:
        raise HTTPException(400, "Se agotaron los intentos para este codigo. Pide uno nuevo")

    if not hmac.compare_digest(registro.codigo_hash, _hash_codigo(usuario.id, codigo.strip())):
        # Se calcula antes del commit: despues, `registro` ya trae el intento sumado.
        quedan = MAX_INTENTOS - (registro.intentos + 1)
        db.execute(
            update(RecuperacionContrasena).where(RecuperacionContrasena.id == registro.id)
            .values(intentos=RecuperacionContrasena.intentos + 1)
        )
        db.commit()
        raise HTTPException(
            400,
            ("El codigo es incorrecto. Te queda 1 intento" if quedan == 1
             else f"El codigo es incorrecto. Te quedan {quedan} intentos") if quedan > 0
            else "El codigo es incorrecto y se agotaron los intentos. Pide uno nuevo",
        )

    # Un solo uso, aunque lleguen dos peticiones con el mismo codigo a la vez.
    consumido = db.execute(
        update(RecuperacionContrasena)
        .where(RecuperacionContrasena.id == registro.id, RecuperacionContrasena.usado == False)  # noqa: E712
        .values(usado=True)
    )
    if consumido.rowcount != 1:
        db.rollback()
        raise invalido
    usuario.password_hash = hash_password(password)
    db.commit()
    return usuario
