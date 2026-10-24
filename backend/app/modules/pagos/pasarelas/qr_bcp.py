"""QR del Banco de Credito de Bolivia (APIs OpenBanking).

Todo lo que sabe del banco vive aqui: la web y la app movil consumen los
endpoints de `pagos/router_qr.py`, que llaman a este archivo. Cambiar de banco
o de version de la API no deberia tocar ningun otro modulo.

Dos operaciones, tal como las define el banco:

    generar(...)  -> POST /Web_ApiQr/api/v3/Qr/Generate   crea el QR a cobrar
    consultar(id) -> POST /Web_ApiQr/api/v3/Qr/Consult    en que estado quedo

El QR no se cobra solo: el cliente lo escanea con su banca movil y el cobro
ocurre fuera de nuestro sistema. Por eso el flujo es "generar y despues
preguntar", nunca "pagar y esperar la respuesta".

Estados que devuelve el banco (spec v3.0, campo `data.status`):

    C = EN COLA        el QR existe y todavia nadie pago  -> seguir esperando
    P = PROCESADO      pagado                             -> cobro aprobado
    V = VENCIDO        se paso de la hora                 -> rechazado
    A = ANULADO        lo anulo la empresa                -> rechazado
    U = PROCESADO POR LA EMPRESA                          -> aprobado

Modos (variable de entorno BCP_MODO):

    simulado  no sale a internet: genera el QR aqui mismo y deja que la pantalla
              decida el desenlace. Permite demostrar los dos caminos sin
              depender del banco ni del certificado.
    sandbox   https://sandbox.openbanking.bcp.com.bo  (credenciales de prueba)
    live      https://openbanking.bcp.com.bo

Sandbox y live exigen TLS mutuo: sin el `.pfx` que entrega el banco, el host
responde 403 antes de leer siquiera las credenciales.
"""
import base64
import io
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.fechas import BOLIVIA
from app.modules.pagos.pasarelas import cliente_http as http

# --------------------------------------------------------------------- estados
EN_COLA, PROCESADO, VENCIDO, ANULADO, POR_EMPRESA = "C", "P", "V", "A", "U"
APROBADOS = {PROCESADO, POR_EMPRESA}
RECHAZADOS = {VENCIDO, ANULADO}

DESCRIPCION = {
    EN_COLA: "EN COLA",
    PROCESADO: "PROCESADO",
    VENCIDO: "VENCIDO",
    ANULADO: "ANULADO",
    POR_EMPRESA: "PROCESADO POR LA EMPRESA",
}

# Codigos de respuesta del host (spec v3.0). "00" es el unico que significa que
# la peticion se atendio bien; el resto son motivos de rechazo.
CODIGOS = {
    "00": "Transaccion completada correctamente",
    "01": "Canal invalido",
    "02": "Password invalido",
    "03": "No tiene acceso a la transaccion",
    "09": "Error en validacion",
    "12": "Transaccion invalida",
    "13": "Monto invalido",
    "30": "Error de formato",
    "51": "No hay fondos suficientes",
    "52": "No se encuentra la cuenta corriente",
    "53": "No se encuentra la cuenta de ahorro",
    "61": "Limite excedido",
    "79": "Cuenta no valida",
    "80": "Transaccion denegada",
    "97": "Error de comunicacion",
    "99": "Error general",
    # No esta en la tabla del manual; lo devuelve el sandbox cuando se consulta
    # un QR que no existe. Se agrega porque sin el, el mensaje que llega al
    # cliente seria "Error no documentado".
    "98": "El QR no existe o no pertenece a esta empresa",
}

BASES = {
    "sandbox": "https://sandbox.openbanking.bcp.com.bo",
    "live": "https://openbanking.bcp.com.bo",
}


@dataclass
class CobroQr:
    """Lo que necesita la pantalla (web o movil) para mostrar y seguir el QR."""

    id: str                  # id que devolvio el banco; con el se consulta
    estado: str              # C | P | V | A | U
    descripcion: str
    imagen_base64: str       # PNG del QR, sin el prefijo "data:image/png;base64,"
    monto: float
    moneda: str
    expira: str              # "yyyy-MM-dd HH:mm", hora de Bolivia
    glosa: str
    correlation_id: str
    simulado: bool
    # Solo cuando el banco ya respondio algo distinto de "en cola".
    numero_operacion: str | None = None
    pagador: str | None = None

    @property
    def aprobado(self) -> bool:
        return self.estado in APROBADOS

    @property
    def rechazado(self) -> bool:
        return self.estado in RECHAZADOS

    def a_dict(self) -> dict:
        return {
            "qr_id": self.id,
            "estado": self.estado,
            "descripcion": self.descripcion,
            "imagen_base64": self.imagen_base64,
            "monto": self.monto,
            "moneda": self.moneda,
            "expira": self.expira,
            "glosa": self.glosa,
            "correlation_id": self.correlation_id,
            "simulado": self.simulado,
            "numero_operacion": self.numero_operacion,
            "pagador": self.pagador,
            "aprobado": self.aprobado,
            "rechazado": self.rechazado,
            "pendiente": self.estado == EN_COLA,
        }


# ------------------------------------------------------------------ configuracion
def modo() -> str:
    return settings.bcp_modo


def esta_configurado() -> tuple[bool, str]:
    """(listo, motivo). En modo simulado siempre esta listo."""
    if modo() == "simulado":
        return True, "Simulador local: no se contacta al banco"
    faltan = [
        nombre for nombre, valor in (
            ("BCP_USUARIO", settings.bcp_usuario),
            ("BCP_PASSWORD", settings.bcp_password),
            ("BCP_APP_USER_ID", settings.bcp_app_user_id),
            ("BCP_PUBLIC_TOKEN", settings.bcp_public_token),
            ("BCP_BUSINESS_CODE", settings.bcp_business_code),
        ) if not valor
    ]
    if not (settings.bcp_cert_pem or settings.bcp_cert_pfx):
        # Sin certificado de cliente el banco corta con 403 antes de mirar el
        # usuario: mas vale decirlo aqui que dejar que falle el cobro.
        faltan.append("BCP_CERT_PEM (o BCP_CERT_PFX)")
    if faltan:
        return False, "Faltan variables de entorno: " + ", ".join(faltan)
    return True, f"Modo {modo()}"


def _base() -> str:
    return BASES[modo()]


def _cabeceras(correlation_id: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Correlation-Id": correlation_id,
        "Authorization": http.basic(settings.bcp_usuario, settings.bcp_password),
    }


def _credenciales() -> dict:
    return {
        "appUserId": settings.bcp_app_user_id,
        "serviceCode": settings.bcp_service_code,
        "businessCode": settings.bcp_business_code,
        "publicToken": settings.bcp_public_token,
    }


def _ssl():
    # tope_tls12: el servidor del BCP no contesta por TLS 1.3 (ver contexto_ssl).
    return http.contexto_ssl(settings.bcp_cert_pfx, settings.bcp_cert_password,
                             settings.bcp_cert_pem, settings.bcp_cert_key,
                             tope_tls12=True)


def nuevo_correlation_id(venta_id: int) -> str:
    """Alfanumerico unico por peticion, como pide la cabecera Correlation-Id."""
    return f"GNG-{venta_id:06d}-{secrets.token_hex(3).upper()}"


def estado_del_servicio() -> dict:
    """Para /api/pagos/metodos: que puede ofrecer hoy la tienda."""
    listo, motivo = esta_configurado()
    return {"modo": modo(), "disponible": listo, "motivo": motivo}


# ---------------------------------------------------------------- generar QR
def generar(venta_id: int, monto: float, glosa: str) -> CobroQr:
    """Crea el QR de cobro. En sandbox/live llama al banco; en simulado lo arma aqui."""
    correlation_id = nuevo_correlation_id(venta_id)
    expira = datetime.now(BOLIVIA) + timedelta(minutes=settings.bcp_qr_minutos)
    expira_txt = expira.strftime("%Y-%m-%d %H:%M")

    if modo() == "simulado":
        return _generar_simulado(venta_id, monto, glosa, correlation_id, expira_txt)

    listo, motivo = esta_configurado()
    if not listo:
        raise http.ErrorPasarela(f"El QR del BCP no esta configurado. {motivo}")

    cuerpo = {
        **_credenciales(),
        "currency": "BOB",
        "amount": round(float(monto), 2),
        "gloss": glosa[:100],
        "expirationDate": expira_txt,
        "singleUse": True,
        "correlationId": correlation_id,
        # El banco guarda estos pares y los devuelve en la consulta: asi sabemos
        # a que venta corresponde un QR aunque la respuesta llegue mucho despues.
        "collectors": [
            {"name": "venta", "parameter": "venta_id", "value": str(venta_id)},
            {"name": "comercio", "parameter": "origen", "value": "GangaClothes"},
        ],
    }
    r = http.pedir(f"{_base()}/Web_ApiQr/api/v3/Qr/Generate",
                   json_body=cuerpo, cabeceras=_cabeceras(correlation_id), ssl_context=_ssl())
    datos = _datos_o_error(r)
    return CobroQr(
        id=str(datos.get("id") or datos.get("qrId") or ""),
        estado=str(datos.get("status") or EN_COLA),
        descripcion=str(datos.get("description") or DESCRIPCION[EN_COLA]),
        imagen_base64=str(datos.get("qrImage") or ""),
        monto=float(datos.get("amount") or monto),
        moneda=str(datos.get("currency") or "BOB"),
        expira=str(datos.get("expirationDate") or expira_txt),
        glosa=str(datos.get("gloss") or glosa),
        correlation_id=correlation_id,
        simulado=False,
    )


def consultar(qr_id: str, venta_id: int) -> CobroQr:
    """Pregunta al banco en que estado quedo el QR."""
    if modo() == "simulado":
        return _consultar_simulado(qr_id)

    correlation_id = nuevo_correlation_id(venta_id)
    cuerpo = {**_credenciales(), "id": int(qr_id) if str(qr_id).isdigit() else qr_id}
    r = http.pedir(f"{_base()}/Web_ApiQr/api/v3/Qr/Consult",
                   json_body=cuerpo, cabeceras=_cabeceras(correlation_id), ssl_context=_ssl())
    datos = _datos_o_error(r)
    estado = str(datos.get("status") or EN_COLA)
    return CobroQr(
        id=str(qr_id),
        estado=estado,
        descripcion=str(datos.get("description") or DESCRIPCION.get(estado, estado)),
        imagen_base64=str(datos.get("qrImage") or ""),
        monto=float(datos.get("amount") or 0),
        moneda=str(datos.get("currency") or "BOB"),
        expira=str(datos.get("expirationDate") or ""),
        glosa=str(datos.get("gloss") or ""),
        correlation_id=str(datos.get("correlationId") or correlation_id),
        simulado=False,
        numero_operacion=_texto(datos.get("operationNumber")),
        pagador=_texto(datos.get("receiverName")),
    )


def _texto(valor) -> str | None:
    texto = str(valor).strip() if valor is not None else ""
    return texto or None


def _datos_o_error(r: http.Respuesta) -> dict:
    """Desarma la respuesta del banco: {"data": {...}, "state": "00", "message": "..."}."""
    if not r.ok:
        raise http.ErrorPasarela(
            f"El banco respondio HTTP {r.estado}: {r.texto[:200] or 'sin cuerpo'}",
            codigo=r.estado, cuerpo=r.texto[:300],
        )
    estado = str(r.cuerpo.get("state") or "")
    if estado and estado != "00":
        motivo = CODIGOS.get(estado) or r.cuerpo.get("message") or "Error no documentado"
        raise http.ErrorPasarela(f"El banco rechazo la peticion ({estado}): {motivo}", codigo=r.estado)
    datos = r.cuerpo.get("data")
    if not isinstance(datos, dict):
        raise http.ErrorPasarela(f"La respuesta del banco no trae el objeto 'data': {r.texto[:200]}")
    return datos


# ==============================================================================
#  Simulador local
# ==============================================================================
# Reproduce el contrato del banco sin salir a internet. Sirve para dos cosas:
# demostrar el flujo completo mientras no este el certificado, y probar los
# desenlaces (pagado, vencido, anulado) sin depender de una banca movil real.
#
# Vive en memoria del proceso: reiniciar el servidor olvida los QR pendientes,
# que es justo lo que hace un QR vencido.
#
# El simulador ademas hace de pagador: a los BCP_SIMULADOR_SEGUNDOS da el QR por
# cobrado. Asi la compra con QR se completa sola, sin que el cliente tenga que
# tocar ningun boton de prueba.
_simulados: dict[str, dict] = {}


def png_qr(contenido: str) -> str:
    """PNG del QR en base64. Es un QR de verdad: se puede escanear."""
    import qrcode

    imagen = qrcode.make(contenido, box_size=8, border=2)
    memoria = io.BytesIO()
    imagen.save(memoria, format="PNG")
    return base64.b64encode(memoria.getvalue()).decode()


def _generar_simulado(venta_id: int, monto: float, glosa: str,
                      correlation_id: str, expira: str) -> CobroQr:
    qr_id = f"SIM{venta_id:06d}{secrets.token_hex(2).upper()}"
    # El contenido imita el de una banca movil: quien lo escanee ve un texto
    # identificable, no una imagen vacia.
    empresa = settings.bcp_business_code or "0366"
    contenido = f"BCP|QR|{empresa}|{qr_id}|BOB|{monto:.2f}|{expira}"
    _simulados[qr_id] = {
        "venta_id": venta_id, "monto": float(monto), "glosa": glosa, "expira": expira,
        "estado": EN_COLA, "correlation_id": correlation_id, "creado": datetime.now(BOLIVIA),
        "imagen": png_qr(contenido), "operacion": None, "pagador": None,
    }
    return _leer_simulado(qr_id)


def _consultar_simulado(qr_id: str) -> CobroQr:
    registro = _simulados.get(qr_id)
    if registro is None:
        raise http.ErrorPasarela(f"El QR {qr_id} no existe o ya no esta en memoria")

    if registro["estado"] == EN_COLA:
        ahora = datetime.now(BOLIVIA)
        # Si se paso la hora y nadie pago, vence solo, igual que en el banco.
        vence = datetime.strptime(registro["expira"], "%Y-%m-%d %H:%M").replace(tzinfo=BOLIVIA)
        if ahora > vence:
            registro["estado"] = VENCIDO
        elif settings.bcp_simulador_segundos > 0:
            # El simulador hace tambien de pagador: pasados unos segundos da el
            # QR por cobrado, como si el cliente lo hubiera escaneado con su
            # banca movil. Sin esto la compra con QR no se puede terminar sin
            # botones de depuracion en la pantalla del cliente.
            # Con BCP_SIMULADOR_SEGUNDOS=0 se queda esperando hasta vencer, que
            # es como se demuestra el desenlace rechazado.
            if (ahora - registro["creado"]).total_seconds() >= settings.bcp_simulador_segundos:
                registro["estado"] = PROCESADO
                registro["operacion"] = f"SIMOP{secrets.randbelow(10 ** 8):08d}"
                registro["pagador"] = "Pagador simulado"
    return _leer_simulado(qr_id)


def marcar_simulado(qr_id: str, estado: str, pagador: str | None = None) -> CobroQr:
    """Fuerza el desenlace de un QR simulado: es lo que dispara el boton de la demo."""
    registro = _simulados.get(qr_id)
    if registro is None:
        raise http.ErrorPasarela(f"El QR {qr_id} no existe o ya no esta en memoria")
    if estado not in DESCRIPCION:
        raise http.ErrorPasarela(f"Estado desconocido: {estado}")
    registro["estado"] = estado
    if estado in APROBADOS:
        registro["operacion"] = f"SIMOP{secrets.randbelow(10 ** 8):08d}"
        registro["pagador"] = pagador or "Pagador de prueba"
    return _leer_simulado(qr_id)


def _leer_simulado(qr_id: str) -> CobroQr:
    r = _simulados[qr_id]
    return CobroQr(
        id=qr_id, estado=r["estado"], descripcion=DESCRIPCION[r["estado"]],
        imagen_base64=r["imagen"], monto=r["monto"], moneda="BOB", expira=r["expira"],
        glosa=r["glosa"], correlation_id=r["correlation_id"], simulado=True,
        numero_operacion=r["operacion"], pagador=r["pagador"],
    )
