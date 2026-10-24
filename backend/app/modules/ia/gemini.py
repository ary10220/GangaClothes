"""Cliente de la API de Gemini (Google AI Studio), capa gratuita.

Es lo unico de este modulo que sale a internet, y hace una sola cosa: mandar la
conversacion y devolver lo que el modelo contesto. No sabe nada de prendas ni de
reportes; de eso se encargan `herramientas.py` y `service.py`.

La conversacion viaja con **las herramientas declaradas**, asi que la respuesta
puede ser de dos clases:

    texto          el modelo ya sabe que contestar
    functionCall   el modelo pide datos: "ejecutame buscar_prendas(color=rojo)"

Quien ejecuta esa llamada y vuelve a preguntar es `service.py`; aqui solo se
traduce el ida y vuelta al formato que espera Google.

**Por que no se usa el SDK de Google.** Con `urllib` alcanza, no agrega una
dependencia mas a `requirements.txt` y deja a la vista que la peticion es un
POST con un JSON. Es el mismo criterio que en las pasarelas de pago.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from app.core.config import settings

TIEMPO_LIMITE = 45  # segundos: una respuesta con herramientas puede tardar

# Errores que justifican probar con el siguiente modelo de la lista.
PASAR_AL_SIGUIENTE = ("HTTP 404", "HTTP 429", "HTTP 500", "HTTP 503")


class ErrorIA(Exception):
    """No se pudo hablar con el modelo. El chat sigue: responde sin el."""


# ------------------------------------------------------------------ estado
def disponible() -> bool:
    return bool(settings.gemini_api)


def modelos() -> list[str]:
    """Modelos a probar en orden. Si Google jubila el primero, sigue el segundo."""
    return [m.strip() for m in settings.gemini_modelos.split(",") if m.strip()]


def estado_del_servicio() -> dict:
    if not disponible():
        return {
            "modo": "sin_modelo",
            "disponible": False,
            "motivo": ("Falta GEMINI_API en el .env. El asistente igual responde, pero sin "
                       "redactar: contesta con los datos en crudo."),
        }
    return {"modo": "gemini", "disponible": True, "modelo": modelos()[0],
            "motivo": "Capa gratuita de Google AI Studio"}


# --------------------------------------------------------- armado del pedido
def turno_usuario(texto: str) -> dict:
    return {"role": "user", "parts": [{"text": texto}]}


def turno_modelo(texto: str) -> dict:
    return {"role": "model", "parts": [{"text": texto}]}


def turno_resultados(resultados: list[tuple[str, dict]]) -> dict:
    """Los resultados de las herramientas, todos en un mismo turno.

    Van con rol de usuario: es informacion que le llega al modelo desde afuera,
    no algo que el haya dicho.

    Ojo: el turno del modelo que PIDIO estas herramientas se le devuelve tal
    cual vino (ver `responder`), no se rearma a mano. Desde Gemini 2 cada
    `functionCall` viene firmada y el servidor exige esa firma de vuelta.
    """
    return {"role": "user",
            "parts": [{"functionResponse": {"name": nombre, "response": resultado}}
                      for nombre, resultado in resultados]}


def _cuerpo(instrucciones: str, contenidos: list[dict], declaraciones: list[dict]) -> dict:
    cuerpo = {
        "systemInstruction": {"parts": [{"text": instrucciones}]},
        "contents": contenidos,
        "generationConfig": {
            # Bajo a proposito: preferimos que repita los datos tal cual a que
            # sea creativo. La gracia del asistente es que no invente.
            "temperature": 0.3,
            "maxOutputTokens": 900,
        },
    }
    if declaraciones:
        cuerpo["tools"] = [{"functionDeclarations": declaraciones}]
        cuerpo["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}
    return cuerpo


# ------------------------------------------------------------------ llamada
def _pedir(modelo: str, cuerpo: dict) -> dict:
    url = f"{settings.gemini_api_base}/models/{modelo}:generateContent"
    peticion = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": settings.gemini_api},
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_LIMITE) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        crudo = e.read().decode("utf-8", errors="replace")
        try:
            detalle = json.loads(crudo).get("error", {}).get("message") or crudo
        except json.JSONDecodeError:
            detalle = crudo
        raise ErrorIA(f"HTTP {e.code}: {detalle[:300]}") from e
    except urllib.error.URLError as e:
        raise ErrorIA(f"No se pudo contactar a Gemini: {e.reason}") from e
    except (TimeoutError, OSError) as e:
        raise ErrorIA(f"Gemini no respondio a tiempo: {e}") from e


def responder(instrucciones: str, contenidos: list[dict],
              declaraciones: list[dict] | None = None) -> dict:
    """Manda la conversacion y devuelve lo que contesto el modelo.

        {"texto": "...", "llamadas": [{"nombre": ..., "argumentos": {...}}]}

    `texto` y `llamadas` no se excluyen: el modelo puede comentar algo y al
    mismo tiempo pedir datos.
    """
    if not disponible():
        raise ErrorIA("No hay clave de Gemini configurada")

    cuerpo = _cuerpo(instrucciones, contenidos, declaraciones or [])
    ultimo_error = None
    for modelo in modelos():
        try:
            return _leer(_pedir(modelo, cuerpo))
        except ErrorIA as e:
            # Hay errores que son del modelo, no de lo que le pedimos: que ya no
            # exista (404), que este saturado (503) o que se paso la cuota del
            # minuto (429). En esos casos se prueba el siguiente de la lista, que
            # es para lo que esta. Con el resto no tiene sentido insistir: el
            # problema es nuestro y lo va a repetir igual.
            if not any(codigo in str(e) for codigo in PASAR_AL_SIGUIENTE):
                raise
            ultimo_error = e
    raise ultimo_error or ErrorIA("Ningun modelo de la lista pudo responder")


def _leer(respuesta: dict) -> dict:
    candidatos = respuesta.get("candidates") or []
    if not candidatos:
        # Pasa cuando el filtro de seguridad de Google bloquea la respuesta.
        motivo = (respuesta.get("promptFeedback") or {}).get("blockReason")
        raise ErrorIA(f"El modelo no devolvio respuesta{f' ({motivo})' if motivo else ''}")

    candidato = candidatos[0]
    partes = (candidato.get("content") or {}).get("parts") or []
    textos, llamadas = [], []
    for parte in partes:
        if parte.get("text"):
            textos.append(parte["text"])
        if parte.get("functionCall"):
            llamada = parte["functionCall"]
            llamadas.append({"nombre": llamada.get("name"), "argumentos": llamada.get("args") or {}})

    if not textos and not llamadas and candidato.get("finishReason") == "MAX_TOKENS":
        raise ErrorIA("La respuesta se corto por largo")

    return {
        "texto": "\n".join(textos).strip(),
        "llamadas": llamadas,
        # El turno tal cual lo mando el modelo. Se le devuelve sin tocar.
        "contenido": candidato.get("content") or {"role": "model", "parts": partes},
    }
