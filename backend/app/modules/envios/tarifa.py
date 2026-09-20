"""Cuanto cuesta un envio y cuanto tarda (CU29).

Este modulo es la UNICA fuente del costo de un envio: lo usan la cotizacion del
checkout, la creacion del envio y el seed. Nadie mas lo calcula por su cuenta,
igual que `promociones/service.py` es el unico que calcula descuentos.

La tarifa tiene que poder explicarse en la defensa, asi que son cuatro reglas y
ninguna sorpresa:

    1. Costo base fijo        Bs 12,00 por salir a repartir
    2. Costo por kilometro    Bs 3,50 x los km hasta el destino
    3. Recargo por urgencia   +45% sobre (1 + 2) si el cliente pide express
    4. Envio gratis           desde Bs 500,00 de compra lo absorbe la tienda

Y un limite: fuera de los 25 km alrededor de la sucursal no se reparte, porque
la distancia se mide en linea recta y mas lejos que eso deja de ser una
aproximacion razonable del recorrido real.

La distancia sale de la formula de Haversine, que da la distancia sobre la
superficie de la Tierra entre dos puntos en latitud y longitud. No es la
distancia por calle: para eso haria falta un servicio de ruteo, y el delivery
de este proyecto es simulado. Por eso el tiempo estimado usa una velocidad
conservadora, que ya descuenta que el recorrido real es mas largo que la recta.

Todo lo que se cobra se calcula en Decimal y se redondea al centavo con medio
centavo hacia arriba, como en el resto del sistema.
"""
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from math import asin, cos, radians, sin, sqrt

from fastapi import HTTPException

CENTAVO = Decimal("0.01")

# ------------------------------------------------------------------ la tarifa
COSTO_BASE = Decimal("12.00")            # Bs que cuesta salir a repartir
COSTO_POR_KM = Decimal("3.50")           # Bs por kilometro hasta el destino
RECARGO_EXPRESS = Decimal("0.45")        # +45% sobre base + distancia
ENVIO_GRATIS_DESDE = Decimal("500.00")   # Bs de compra a partir de los cuales es gratis
RADIO_COBERTURA_KM = Decimal("25")       # mas lejos que esto no se reparte

# ------------------------------------------------------------------ el tiempo
MINUTOS_PREPARACION = 45                 # armar el pedido en la sucursal
MINUTOS_PREPARACION_EXPRESS = 15         # el express se arma primero
VELOCIDAD_KMH = Decimal("18")            # moto en ciudad, con trafico y semaforos

# Radio medio de la Tierra (media aritmetica de la IUGG), en km.
RADIO_TIERRA_KM = 6371.0088


# -------------------------------------------------------------------- formato
def _dinero(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _bs(valor) -> str:
    """12.5 -> "Bs 12,50", con la coma decimal que se usa en Bolivia."""
    return f"Bs {_dinero(valor)}".replace(".", ",")


def _km(valor) -> str:
    return f"{Decimal(str(valor)).quantize(CENTAVO)} km".replace(".", ",")


# ------------------------------------------------------------------ distancia
def validar_coordenadas(latitud, longitud, que: str = "El destino") -> None:
    if latitud is None or longitud is None:
        raise HTTPException(400, f"{que} no tiene coordenadas: marcalo en el mapa")
    if not (-90 <= float(latitud) <= 90) or not (-180 <= float(longitud) <= 180):
        raise HTTPException(400, f"{que} tiene coordenadas fuera de rango")


def distancia_km(lat1, lon1, lat2, lon2) -> Decimal:
    """Formula de Haversine: distancia en linea recta sobre la superficie terrestre.

        a = sin^2(dlat/2) + cos(lat1) * cos(lat2) * sin^2(dlon/2)
        d = 2 * R * asin(raiz(a))

    Se usa asin(raiz(a)) y no atan2 porque para distancias de ciudad dan lo
    mismo y asi se lee igual que la formula del libro.
    """
    lat1, lon1, lat2, lon2 = map(radians, (float(lat1), float(lon1), float(lat2), float(lon2)))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return Decimal(str(2 * RADIO_TIERRA_KM * asin(sqrt(a)))).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def minutos_estimados(distancia, express: bool = False) -> int:
    """Preparar el pedido en la sucursal + recorrer la distancia hasta el destino."""
    preparacion = MINUTOS_PREPARACION_EXPRESS if express else MINUTOS_PREPARACION
    viaje = (Decimal(str(distancia)) / VELOCIDAD_KMH) * 60
    return int(preparacion + viaje.to_integral_value(rounding=ROUND_HALF_UP))


# ----------------------------------------------------------------- cotizacion
def cotizar(distancia, monto_compra, express: bool = False) -> dict:
    """Desglose completo del envio, para mostrarselo al cliente ANTES de pagar.

    Devuelve siempre el desglose entero (base, distancia, recargo y, si
    corresponde, la bonificacion por envio gratis) y no solo el total: el
    cliente tiene que poder ver de donde sale cada boliviano.
    """
    distancia = Decimal(str(distancia)).quantize(CENTAVO)
    monto = _dinero(monto_compra)

    por_distancia = _dinero(COSTO_POR_KM * distancia)
    subtotal = _dinero(COSTO_BASE + por_distancia)
    recargo = _dinero(subtotal * RECARGO_EXPRESS) if express else Decimal("0.00")
    costo = _dinero(subtotal + recargo)

    desglose = [
        {"concepto": "Costo base del envio",
         "detalle": "tarifa fija por salir a repartir",
         "importe": float(COSTO_BASE)},
        {"concepto": "Distancia hasta tu direccion",
         "detalle": f"{_km(distancia)} x {_bs(COSTO_POR_KM)} por km",
         "importe": float(por_distancia)},
    ]
    if express:
        desglose.append({
            "concepto": "Recargo por entrega express",
            "detalle": f"+{int(RECARGO_EXPRESS * 100)}% sobre {_bs(subtotal)} por la prioridad",
            "importe": float(recargo),
        })

    gratis = monto >= ENVIO_GRATIS_DESDE
    if gratis:
        # El envio gratis tapa TODO el costo, recargo express incluido: es mas
        # facil de explicar en la pantalla y es mejor para el cliente.
        desglose.append({
            "concepto": f"Envio gratis por compra desde {_bs(ENVIO_GRATIS_DESDE)}",
            "detalle": f"tu compra es de {_bs(monto)}: el envio lo pone la tienda",
            "importe": float(-costo),
        })
        costo = Decimal("0.00")

    return {
        "distancia_km": float(distancia),
        "express": express,
        "dentro_de_cobertura": distancia <= RADIO_COBERTURA_KM,
        "cobertura_km": float(RADIO_COBERTURA_KM),
        "desglose": desglose,
        "costo_envio": float(costo),
        "gratis": gratis,
        # Cuanto le falta a la compra para que el envio salga gratis (0 si ya lo es).
        "falta_para_envio_gratis": float(max(ENVIO_GRATIS_DESDE - monto, Decimal("0"))),
        "envio_gratis_desde": float(ENVIO_GRATIS_DESDE),
        "minutos_estimados": minutos_estimados(distancia, express),
    }


def fecha_estimada(minutos: int, desde: datetime | None = None) -> datetime:
    """Instante en UTC y sin zona, como los guarda el resto del sistema."""
    base = desde or datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    return base + timedelta(minutes=minutos)


def parametros() -> dict:
    """La tarifa vigente, para mostrarla en la pantalla y documentarla en /docs."""
    return {
        "costo_base": float(COSTO_BASE),
        "costo_por_km": float(COSTO_POR_KM),
        "recargo_express_porcentaje": float(RECARGO_EXPRESS * 100),
        "envio_gratis_desde": float(ENVIO_GRATIS_DESDE),
        "cobertura_km": float(RADIO_COBERTURA_KM),
        "minutos_preparacion": MINUTOS_PREPARACION,
        "minutos_preparacion_express": MINUTOS_PREPARACION_EXPRESS,
        "velocidad_kmh": float(VELOCIDAD_KMH),
    }
