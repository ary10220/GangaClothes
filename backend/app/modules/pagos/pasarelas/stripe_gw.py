"""Tarjeta por Stripe, en modo prueba.

Como en `qr_bcp.py`, este archivo es lo unico que sabe hablar con el proveedor.
Expone una sola operacion util para el negocio:

    cobrar(venta_id, monto, descripcion, numero_tarjeta) -> Cobro

El numero de tarjeta **no viaja a Stripe**. Stripe tiene deshabilitada por
defecto la API de tarjetas en crudo (es lo que evita que un comercio guarde
numeros reales), asi que lo que se manda es un *payment method* de prueba ya
creado por ellos. El numero que escribe el cliente solo elige cual:

    4242 4242 4242 4242  -> pm_card_visa                             aprobado
    4000 0000 0000 0002  -> pm_card_chargeDeclined                   rechazada
    4000 0000 0000 9995  -> pm_card_chargeDeclinedInsufficientFunds  sin fondos
    4000 0000 0000 0069  -> pm_card_chargeDeclinedExpiredCard        vencida

Esos numeros son los publicos de docs.stripe.com/testing, los mismos que pide
cualquier integracion en modo prueba. **Cualquier otro numero se rechaza**: en
modo prueba no hay forma de cobrarle a una tarjeta inventada, y dar por bueno un
numero cualquiera haria creer que la pasarela cobra cuando no cobro nada.

Modos:

    STRIPE_SECRET_KEY vacia -> simulado: no sale a internet, el desenlace lo
                               decide la misma tabla de arriba.
    sk_test_...             -> llama de verdad a api.stripe.com (modo prueba:
                               no se mueve dinero).
    sk_live_...             -> se rechaza: este proyecto no cobra dinero real.
"""
import secrets
from dataclasses import dataclass

from app.core.config import settings
from app.modules.pagos.pasarelas import cliente_http as http

# Stripe cobra en la unidad minima: BOB no es moneda sin decimales, van centavos.
MULTIPLICADOR = 100

# numero de tarjeta (sin espacios) -> payment method de prueba de Stripe
TARJETAS_PRUEBA = {
    "4242424242424242": ("pm_card_visa", True, None),
    "5555555555554444": ("pm_card_mastercard", True, None),
    "4000000000000002": ("pm_card_chargeDeclined", False,
                         "La tarjeta fue rechazada por el banco emisor (card_declined)"),
    "4000000000009995": ("pm_card_chargeDeclinedInsufficientFunds", False,
                         "La tarjeta no tiene fondos suficientes (insufficient_funds)"),
    "4000000000000069": ("pm_card_chargeDeclinedExpiredCard", False,
                         "La tarjeta esta vencida (expired_card)"),
    "4000000000000127": ("pm_card_chargeDeclinedIncorrectCvc", False,
                         "El codigo de seguridad es incorrecto (incorrect_cvc)"),
}
# Un numero que no este en la tabla NO se cobra. En modo prueba Stripe solo
# acepta sus tarjetas de prueba: dar por buena cualquier cifra de 16 digitos
# seria mentir sobre lo que la pasarela puede hacer.
NO_ES_DE_PRUEBA = (
    "Esa tarjeta no existe en el entorno de prueba. Usa 4242 4242 4242 4242 para que el "
    "pago se apruebe, o 4000 0000 0000 0002 para ver un rechazo del banco emisor."
)

# Mensajes de Stripe traducidos; si llega uno nuevo se muestra el de Stripe.
MOTIVOS = {
    # Stripe manda el motivo fino en `decline_code` y el grueso en `code`; se
    # miran los dos, asi que la tabla tiene entradas de ambos.
    "generic_decline": "La tarjeta fue rechazada por el banco emisor",
    "card_declined": "La tarjeta fue rechazada por el banco emisor",
    "lost_card": "La tarjeta figura como extraviada",
    "stolen_card": "La tarjeta figura como robada",
    "do_not_honor": "El banco emisor no autorizo el cobro",
    "insufficient_funds": "La tarjeta no tiene fondos suficientes",
    "expired_card": "La tarjeta esta vencida",
    "incorrect_cvc": "El codigo de seguridad es incorrecto",
    "processing_error": "El banco emisor no pudo procesar la tarjeta",
}


@dataclass
class Cobro:
    """Resultado de intentar cobrar. `aprobado` es lo unico que mira el negocio."""

    aprobado: bool
    referencia: str          # id del PaymentIntent: pi_...
    estado: str              # succeeded | requires_payment_method | ...
    motivo: str | None       # por que se rechazo, en castellano
    monto: float
    moneda: str
    marca: str | None        # visa, mastercard...
    ultimos4: str | None
    simulado: bool

    def a_dict(self) -> dict:
        return {
            "aprobado": self.aprobado, "referencia": self.referencia, "estado": self.estado,
            "motivo": self.motivo, "monto": self.monto, "moneda": self.moneda,
            "marca": self.marca, "ultimos4": self.ultimos4, "simulado": self.simulado,
        }


# ------------------------------------------------------------------ configuracion
def esta_configurado() -> tuple[bool, str]:
    clave = settings.stripe_secret_key
    if not clave:
        return True, "Simulador local: definir STRIPE_SECRET_KEY para cobrar contra Stripe"
    if clave.startswith("sk_live_"):
        return False, "STRIPE_SECRET_KEY es una clave de produccion: este proyecto solo cobra en modo prueba"
    if not clave.startswith("sk_test_"):
        return False, "STRIPE_SECRET_KEY no parece una clave de Stripe (deberia empezar con sk_test_)"
    return True, "Modo prueba contra api.stripe.com"


def es_simulado() -> bool:
    return not settings.stripe_secret_key


def estado_del_servicio() -> dict:
    listo, motivo = esta_configurado()
    return {
        "modo": "simulado" if es_simulado() else "prueba",
        "disponible": listo,
        "motivo": motivo,
        # La clave publica no es secreta: identifica la cuenta ante el navegador.
        "clave_publica": settings.stripe_public_key or None,
    }


def _moneda() -> str:
    return "bob"


def solo_digitos(numero: str) -> str:
    return "".join(c for c in (numero or "") if c.isdigit())


def _metodo_de_prueba(numero: str) -> tuple[str, bool, str | None] | None:
    """La tarjeta de prueba que corresponde al numero, o None si no es ninguna."""
    return TARJETAS_PRUEBA.get(solo_digitos(numero))


# ------------------------------------------------------------------------ cobrar
def cobrar(venta_id: int, monto: float, descripcion: str, numero_tarjeta: str) -> Cobro:
    """Intenta cobrar el total de una venta. Nunca lanza por un rechazo: un
    rechazo es un resultado normal y vuelve como `aprobado=False`."""
    listo, motivo = esta_configurado()
    if not listo:
        raise http.ErrorPasarela(f"Stripe no esta configurado. {motivo}")

    tarjeta = _metodo_de_prueba(numero_tarjeta)
    if tarjeta is None:
        # No se llama a Stripe: no hay nada que cobrar con un numero inventado.
        # Vuelve como rechazo, no como error, para que el carrito quede intacto
        # y el cliente pueda corregir y reintentar.
        digitos = solo_digitos(numero_tarjeta)
        return Cobro(
            aprobado=False, referencia="", estado="numero_no_valido",
            motivo=NO_ES_DE_PRUEBA, monto=float(monto), moneda="BOB",
            marca=None, ultimos4=digitos[-4:] if len(digitos) >= 4 else None,
            simulado=es_simulado(),
        )

    metodo, aprueba, texto_rechazo = tarjeta
    if es_simulado():
        return _cobrar_simulado(monto, metodo, aprueba, texto_rechazo, numero_tarjeta)

    centavos = int(round(float(monto) * MULTIPLICADOR))
    datos = {
        "amount": centavos,
        "currency": _moneda(),
        "payment_method": metodo,
        "confirm": "true",
        "description": descripcion[:200],
        # Sin esto Stripe puede pedir una redireccion (3-D Secure) que esta
        # pantalla no sabe atender; asi el resultado llega en la misma llamada.
        "automatic_payment_methods[enabled]": "true",
        "automatic_payment_methods[allow_redirects]": "never",
        "metadata[venta_id]": str(venta_id),
        "metadata[origen]": "GangaClothes",
        # Sin expandir, `latest_charge` viene como un id y no traeria la marca
        # ni los ultimos 4 digitos, que son los que se imprimen en el comprobante.
        "expand[]": "latest_charge",
    }
    r = http.pedir(
        f"{settings.stripe_api_base}/payment_intents",
        form=datos,
        cabeceras={
            "Authorization": f"Bearer {settings.stripe_secret_key}",
            # Si la red corta la respuesta y se reintenta, Stripe no cobra dos veces.
            "Idempotency-Key": f"ganga-venta-{venta_id}-{secrets.token_hex(6)}",
        },
    )
    return _leer_respuesta(r, monto)


def _leer_respuesta(r: http.Respuesta, monto: float) -> Cobro:
    cuerpo = r.cuerpo

    # Un rechazo de tarjeta llega como HTTP 402 con error.type=card_error y,
    # dentro, el PaymentIntent que quedo. Eso NO es un fallo de integracion.
    error = cuerpo.get("error") or {}
    if error:
        if error.get("type") != "card_error":
            raise http.ErrorPasarela(
                f"Stripe rechazo la peticion: {error.get('message') or r.texto[:200]}",
                codigo=r.estado, cuerpo=r.texto[:300],
            )
        intento = error.get("payment_intent") or {}
        codigo = error.get("decline_code") or error.get("code") or "card_declined"
        tarjeta = _tarjeta_de(intento)
        return Cobro(
            aprobado=False,
            referencia=str(intento.get("id") or "pi_desconocido"),
            estado=str(intento.get("status") or "requires_payment_method"),
            motivo=MOTIVOS.get(codigo, error.get("message") or codigo),
            monto=monto, moneda="BOB", marca=tarjeta[0], ultimos4=tarjeta[1], simulado=False,
        )

    if not r.ok:
        raise http.ErrorPasarela(f"Stripe respondio HTTP {r.estado}: {r.texto[:200]}", codigo=r.estado)

    estado = str(cuerpo.get("status") or "")
    marca, ultimos4 = _tarjeta_de(cuerpo)
    return Cobro(
        aprobado=estado == "succeeded",
        referencia=str(cuerpo.get("id") or ""),
        estado=estado or "desconocido",
        motivo=None if estado == "succeeded" else f"Stripe dejo el pago en estado '{estado}'",
        monto=float(cuerpo.get("amount_received") or cuerpo.get("amount") or 0) / MULTIPLICADOR or monto,
        moneda=str(cuerpo.get("currency") or "bob").upper(),
        marca=marca, ultimos4=ultimos4, simulado=False,
    )


def _tarjeta_de(intento: dict) -> tuple[str | None, str | None]:
    """Marca y ultimos 4 digitos, que Stripe deja en el cargo del PaymentIntent."""
    cargo = ((intento.get("latest_charge") or {}) if isinstance(intento.get("latest_charge"), dict) else {})
    detalle = ((cargo.get("payment_method_details") or {}).get("card") or {})
    if not detalle:
        detalle = ((intento.get("payment_method") or {}).get("card") or {}) \
            if isinstance(intento.get("payment_method"), dict) else {}
    return detalle.get("brand"), detalle.get("last4")


# ------------------------------------------------------------------- simulador
def _cobrar_simulado(monto: float, metodo: str, aprueba: bool,
                     motivo: str | None, numero: str) -> Cobro:
    digitos = solo_digitos(numero)
    return Cobro(
        aprobado=aprueba,
        referencia=f"pi_sim_{secrets.token_hex(12)}",
        estado="succeeded" if aprueba else "requires_payment_method",
        motivo=None if aprueba else (motivo or "La tarjeta fue rechazada"),
        monto=float(monto), moneda="BOB",
        marca="mastercard" if metodo.endswith("mastercard") else "visa",
        ultimos4=digitos[-4:] if len(digitos) >= 4 else None,
        simulado=True,
    )
