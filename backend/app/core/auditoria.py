"""Escritura de la bitacora.

Se llama desde los routers despues de que la operacion salio bien. Nunca debe
hacer fallar la peticion: si el registro no se puede guardar, se descarta.
"""
from fastapi import Request

from app.models.seguridad import Bitacora


def _ip(peticion: Request | None) -> str | None:
    if peticion is None:
        return None
    # Detras de un proxy (Render) la IP real viene en X-Forwarded-For.
    reenviada = peticion.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return peticion.client.host if peticion.client else None


def texto_actor(usuario) -> str:
    if usuario is None:
        return "Sistema"
    nombre = " ".join(filter(None, [usuario.nombre, usuario.apellido]))
    return f"{nombre} <{usuario.email}>"


def registrar(
    db,
    *,
    modulo: str,
    accion: str,
    usuario=None,
    peticion: Request | None = None,
    entidad: str | None = None,
    entidad_id: int | None = None,
    detalle: str | None = None,
    nivel: str = "INFO",
) -> None:
    """Agrega una fila a la bitacora y la confirma."""
    try:
        db.add(Bitacora(
            usuario_id=getattr(usuario, "id", None),
            actor=texto_actor(usuario),
            modulo=modulo.upper(),
            accion=accion.upper(),
            nivel=nivel.upper(),
            entidad=entidad,
            entidad_id=entidad_id,
            detalle=(detalle or "")[:400] or None,
            ip=_ip(peticion),
        ))
        db.commit()
    except Exception:
        # La accion del usuario ya se completo: un fallo al auditar no la revierte.
        db.rollback()
