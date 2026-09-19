"""Fechas del sistema: una sola definicion de la zona horaria.

La base guarda instantes en UTC y sin zona (`server_default=func.now()` y
`datetime.utcnow()`). Al salir por la API se marcan con "Z" para que cualquier
cliente (web, Flutter) sepa que son UTC y los muestre en la hora de quien mira.
Lo que se agrupa o se imprime por dia usa la hora de Bolivia (UTC-4, sin
horario de verano).

Excepcion: `reserva.fecha_hora_prueba` NO es un instante UTC sino la hora de la
tienda tal como la eligio el cliente; se guarda y se devuelve sin zona.
"""
from datetime import date, datetime, timedelta, timezone

BOLIVIA = timezone(timedelta(hours=-4))


def utc_iso(fecha: datetime | None) -> str | None:
    """Instante de la base -> texto ISO en UTC: "2026-09-19T22:42:27Z"."""
    if fecha is None:
        return None
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone(timezone.utc).replace(tzinfo=None)
    return f"{fecha.replace(microsecond=0).isoformat()}Z"


def a_bolivia(fecha: datetime | None) -> datetime | None:
    """Instante UTC de la base -> hora de Bolivia (sin zona), para agrupar o imprimir."""
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        fecha = fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(BOLIVIA).replace(tzinfo=None)


def hoy_bolivia() -> date:
    """El 'hoy' del negocio: a las 21:00 en Bolivia todavia es el mismo dia."""
    return a_bolivia(datetime.now(timezone.utc)).date()


def texto_bolivia(iso: str | None, con_hora: bool = True) -> str:
    """Texto ISO en UTC -> "19/09/2026 18:42" en hora de Bolivia (para los CSV)."""
    if not iso:
        return ""
    try:
        fecha = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    local = a_bolivia(fecha) if fecha.tzinfo else fecha
    return local.strftime("%d/%m/%Y %H:%M" if con_hora else "%d/%m/%Y")
