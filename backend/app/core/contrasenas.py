"""Regla para las contrasenas nuevas: registro, alta de usuarios y recuperacion.

No se aplica al iniciar sesion: las cuentas creadas antes de la regla siguen
entrando con su contrasena. La web (shared/contrasena) muestra la misma lista.
"""
import re

from fastapi import HTTPException

LETRAS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"

REGLAS = [
    (re.compile(r".{8,}", re.S), "al menos 8 caracteres"),
    (re.compile(r"[A-ZÁÉÍÓÚÜÑ]"), "una mayuscula"),
    (re.compile(r"[a-záéíóúüñ]"), "una minuscula"),
    (re.compile(r"\d"), "un numero"),
    (re.compile(rf"[^{LETRAS}0-9\s]"), "un caracter especial (! @ # $ % & * . - _)"),
]


def faltantes(password: str) -> list[str]:
    return [texto for patron, texto in REGLAS if not patron.search(password)]


def exigir_segura(password: str) -> None:
    # bcrypt solo usa los primeros 72 bytes: mas largo daria una falsa seguridad.
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(400, "La contrasena es demasiado larga (maximo 72 bytes)")
    falta = faltantes(password)
    if falta:
        lista = falta[0] if len(falta) == 1 else ", ".join(falta[:-1]) + " y " + falta[-1]
        raise HTTPException(400, f"La contrasena debe tener {lista}")
