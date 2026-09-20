"""Llamadas HTTPS a las pasarelas, con la biblioteca estandar.

Dos cosas que no trae `urllib` de fabrica y aqui si estan:

1. **Certificado de cliente.** El sandbox del BCP hace TLS mutuo: si el cliente
   no presenta su certificado, IIS corta con 403 antes de mirar el usuario y la
   contrasena. El banco entrega un `.pfx` y Python solo sabe leer PEM, asi que
   se convierte una vez y se deja en un archivo temporal con permisos propios.
2. **Errores que no tumban la peticion.** Cualquier fallo de red o de formato
   sale como `ErrorPasarela`, que el servicio traduce a un rechazo ordenado.
"""
import atexit
import base64
import json
import os
import ssl
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

TIEMPO_LIMITE = 30  # segundos


class ErrorPasarela(Exception):
    """La pasarela no se pudo consultar o respondio algo que no se entiende."""

    def __init__(self, mensaje: str, codigo: int | None = None, cuerpo: str | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo
        self.cuerpo = cuerpo


@dataclass
class Respuesta:
    estado: int
    cuerpo: dict = field(default_factory=dict)
    texto: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.estado < 300


# --------------------------------------------------------------- certificado
_pem_en_uso: dict[str, str] = {}


def _borrar_pems() -> None:
    for ruta in _pem_en_uso.values():
        try:
            os.unlink(ruta)
        except OSError:
            pass


atexit.register(_borrar_pems)


def _pfx_a_pem(ruta_pfx: str, password: str) -> str:
    """Convierte el .pfx del banco en un PEM temporal y devuelve su ruta.

    Se hace una sola vez por archivo: el resultado queda cacheado mientras viva
    el proceso y se borra al salir.
    """
    if ruta_pfx in _pem_en_uso and os.path.exists(_pem_en_uso[ruta_pfx]):
        return _pem_en_uso[ruta_pfx]

    if not os.path.exists(ruta_pfx):
        raise ErrorPasarela(f"No se encuentra el certificado del banco en {ruta_pfx}")

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.serialization import pkcs12

    with open(ruta_pfx, "rb") as f:
        datos = f.read()
    clave_bytes = password.encode() if password else None
    try:
        privada, certificado, cadena = pkcs12.load_key_and_certificates(datos, clave_bytes)
    except ValueError as e:
        raise ErrorPasarela(f"No se pudo abrir el certificado .pfx (revisa BCP_CERT_PASSWORD): {e}") from e
    if privada is None or certificado is None:
        raise ErrorPasarela("El .pfx no trae la clave privada y el certificado juntos")

    partes = [
        privada.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        certificado.public_bytes(serialization.Encoding.PEM),
    ]
    partes += [c.public_bytes(serialization.Encoding.PEM) for c in (cadena or [])]

    # delete=False porque el contexto SSL lo abre por ruta; se borra en atexit.
    descriptor, ruta_pem = tempfile.mkstemp(suffix=".pem", prefix="bcp_")
    with os.fdopen(descriptor, "wb") as f:
        f.write(b"".join(partes))
    os.chmod(ruta_pem, 0o600)
    _pem_en_uso[ruta_pfx] = ruta_pem
    return ruta_pem


def contexto_ssl(ruta_pfx: str = "", password: str = "",
                 ruta_pem: str = "", ruta_clave: str = "",
                 tope_tls12: bool = False) -> ssl.SSLContext:
    """Contexto TLS con nuestro certificado de cliente, si hay uno.

    Se prefiere el par PEM (.crt + .key) cuando esta: es lo que OpenSSL lee
    directo, sin convertir nada ni necesitar la contrasena del .pfx.

    `tope_tls12` limita el handshake a TLS 1.2. Hace falta para el BCP: con
    TLS 1.3 su servidor completa el handshake y despues **cierra la conexion sin
    responder**, y la peticion muere con un "Remote end closed connection". Es
    la misma configuracion que su manual pide hacer a mano en Postman
    ("TLS/SSL protocols disabled during handshake").
    """
    ctx = ssl.create_default_context()
    if tope_tls12:
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    if ruta_pem:
        if not os.path.exists(ruta_pem):
            raise ErrorPasarela(f"No se encuentra el certificado del banco en {ruta_pem}")
        if ruta_clave and not os.path.exists(ruta_clave):
            raise ErrorPasarela(f"No se encuentra la clave privada en {ruta_clave}")
        try:
            # keyfile=None significa "la clave esta en el mismo archivo".
            ctx.load_cert_chain(ruta_pem, ruta_clave or None, password or None)
        except ssl.SSLError as e:
            raise ErrorPasarela(f"No se pudo cargar el certificado PEM del banco: {e}") from e
    elif ruta_pfx:
        ctx.load_cert_chain(_pfx_a_pem(ruta_pfx, password))
    return ctx


# ------------------------------------------------------------------ peticion
def basic(usuario: str, password: str) -> str:
    return "Basic " + base64.b64encode(f"{usuario}:{password}".encode()).decode()


def pedir(
    url: str,
    *,
    metodo: str = "POST",
    json_body: dict | None = None,
    form: dict | None = None,
    cabeceras: dict[str, str] | None = None,
    ssl_context: ssl.SSLContext | None = None,
    tiempo_limite: int = TIEMPO_LIMITE,
) -> Respuesta:
    """Una peticion HTTPS. Devuelve la respuesta aunque el estado sea 4xx: las
    pasarelas mandan el motivo del rechazo en el cuerpo de un 402 o un 400."""
    cabeceras = dict(cabeceras or {})
    datos: bytes | None = None
    if json_body is not None:
        datos = json.dumps(json_body).encode()
        cabeceras.setdefault("Content-Type", "application/json")
    elif form is not None:
        datos = urllib.parse.urlencode(form, doseq=True).encode()
        cabeceras.setdefault("Content-Type", "application/x-www-form-urlencoded")

    peticion = urllib.request.Request(url, data=datos, method=metodo, headers=cabeceras)
    try:
        with urllib.request.urlopen(peticion, timeout=tiempo_limite, context=ssl_context) as r:
            return _leer(r.status, r.read())
    except urllib.error.HTTPError as e:
        cuerpo = e.read()
        respuesta = _leer(e.code, cuerpo)
        # 403 sin cuerpo JSON es el sintoma tipico de TLS mutuo sin certificado.
        if e.code == 403 and not respuesta.cuerpo:
            raise ErrorPasarela(
                "El servidor rechazo la conexion (403). Falta el certificado de cliente "
                "o no corresponde a estas credenciales.",
                codigo=403, cuerpo=respuesta.texto[:300],
            ) from e
        return respuesta
    except urllib.error.URLError as e:
        raise ErrorPasarela(f"No se pudo contactar la pasarela: {e.reason}") from e
    except (TimeoutError, OSError) as e:
        raise ErrorPasarela(f"La pasarela no respondio a tiempo: {e}") from e


def _leer(estado: int, crudo: bytes) -> Respuesta:
    texto = crudo.decode("utf-8", errors="replace")
    try:
        cuerpo = json.loads(texto) if texto.strip() else {}
    except json.JSONDecodeError:
        cuerpo = {}
    return Respuesta(estado=estado, cuerpo=cuerpo if isinstance(cuerpo, dict) else {"data": cuerpo}, texto=texto)
