"""Recomendador propio (CU28).

Esta es la parte del modulo que **no** depende de ningun servicio externo: es
nuestro modelo, y es quien decide que prendas sugerir. El asistente conversa,
pero el criterio sale de aqui.

Como funciona, en una frase: se arma un **perfil de gustos** del cliente con lo
que compro, reservo y miro, y despues se puntua cada prenda del catalogo segun
cuanto se parece a ese perfil.

    perfil = {"categoria": {"Vestidos": 8, "Tops": 3},
              "color":     {"Negro": 6, "Blanco": 2},
              "marca":     {"ONLY": 4}, ...}

Las senales pesan distinto, porque no dicen lo mismo:

    comprar   3  puso plata: es lo que mas dice de su gusto
    reservar  2  se tomo el trabajo de ir a probarselo
    mirar     1  le llamo la atencion, nada mas

Y el puntaje de cada prenda suma seis cosas (los pesos estan en PESOS, abajo):

    categoria · color · marca · coleccion · cercania de precio · popularidad

mas dos ajustes: bonus si esta en promocion y bonus si hay stock en la talla
que el cliente suele usar.

Todo es explicable: cada recomendacion viene con el `motivo` que mas peso tuvo
("porque compraste vestidos negros"), no con un numero suelto. Eso es a proposito
— en la defensa hay que poder responder por que aparecio cada prenda.

**El catalogo se lee siempre en vivo** (`prendas.service.armar_catalogo`), nunca
de una copia guardada: una prenda que se publica ahora puede recomendarse en la
siguiente consulta, y una que se queda sin stock deja de aparecer sola.
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.fechas import hoy_bolivia
from app.models.catalogo import (Categoria, Coleccion, Color, Prenda, Talla,
                                 Temporada, Variante)
from app.models.ia import EventoNavegacion, Recomendacion
from app.models.usuarios import Cliente
from app.models.ventas import DetalleReserva, DetalleVenta, Reserva, Venta
from app.modules.prendas import service as prendas

# Cuanto vale cada senal al armar el perfil de gustos.
PESO_SENAL = {"compra": 3.0, "reserva": 2.0, "vista": 1.0}

# Cuanto aporta cada coincidencia al puntaje final de una prenda.
PESOS = {
    "categoria": 3.0,
    "color": 2.0,
    "marca": 1.5,
    "coleccion": 1.0,
    "precio": 1.5,      # que este en el rango que el cliente suele gastar
    "popularidad": 1.0,  # lo que mas se vende, para no recomendar rarezas
}
BONUS_PROMOCION = 1.2
BONUS_TALLA = 1.0

# Ventana para medir que se esta vendiendo ahora.
DIAS_POPULARIDAD = 60


# ========================================================= catalogo legible
def catalogo(db: Session, *, sucursal_id: int | None = None, **filtros) -> list[dict]:
    """El catalogo publicado, con los nombres que faltan para poder hablar de el.

    `armar_catalogo` devuelve `categoria_id` y `coleccion_id`, que sirven para
    filtrar pero no para redactar una frase. Aqui se agregan el nombre de la
    categoria, la coleccion, la temporada y la lista de colores con stock, que
    es lo que necesitan tanto los motivos de la recomendacion como el asistente.

    Se consulta en vivo: una prenda publicada hace un minuto ya sale aqui.
    """
    items = prendas.armar_catalogo(db, solo_publicadas=True, sucursal_id=sucursal_id, **filtros)
    if not items:
        return []

    categorias = {c.id: c.nombre for c in db.query(Categoria).all()}
    colecciones = {c.id: (c.nombre, c.temporada_id) for c in db.query(Coleccion).all()}
    temporadas = {t.id: t.nombre for t in db.query(Temporada).all()}

    for item in items:
        nombre_coleccion, temporada_id = colecciones.get(item["coleccion_id"], (None, None))
        item["categoria"] = categorias.get(item["categoria_id"])
        item["coleccion"] = nombre_coleccion
        item["temporada"] = temporadas.get(temporada_id)
        # Solo lo que de verdad se puede llevar hoy.
        item["colores"] = sorted({v["color"] for v in item["variantes"]
                                  if (v.get("disponible_total") or 0) > 0})
        item["tallas"] = sorted({v["talla"] for v in item["variantes"]
                                 if (v.get("disponible_total") or 0) > 0})
    return items


# ============================================================ perfil de gustos
def _lineas_compradas(db: Session, cliente_id: int):
    """Prenda y cantidad de cada linea que el cliente pago."""
    return (
        db.query(Prenda, Variante, Talla, Color, DetalleVenta.cantidad)
        .join(DetalleVenta, DetalleVenta.variante_id == Variante.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(Venta.cliente_id == cliente_id, Venta.estado == "pagada")
        .all()
    )


def _lineas_reservadas(db: Session, cliente_id: int):
    return (
        db.query(Prenda, Variante, Talla, Color, DetalleReserva.cantidad)
        .join(DetalleReserva, DetalleReserva.variante_id == Variante.id)
        .join(Reserva, Reserva.id == DetalleReserva.reserva_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(Reserva.cliente_id == cliente_id)
        .all()
    )


def _prendas_vistas(db: Session, cliente_id: int):
    """Prendas que el cliente abrio en la tienda, con cuantas veces."""
    return (
        db.query(Prenda, func.count(EventoNavegacion.id))
        .join(EventoNavegacion, EventoNavegacion.prenda_id == Prenda.id)
        .filter(EventoNavegacion.cliente_id == cliente_id)
        .group_by(Prenda.id)
        .all()
    )


def perfil(db: Session, cliente_id: int) -> dict:
    """Los gustos del cliente, contados por atributo.

    Devuelve tambien `prendas_compradas` (para no recomendar lo que ya tiene),
    `tallas` (la que mas usa) y `precio_medio` de lo que suele gastar.
    """
    gustos = {"categoria": defaultdict(float), "color": defaultdict(float),
              "marca": defaultdict(float), "coleccion": defaultdict(float)}
    tallas = defaultdict(float)
    compradas: set[int] = set()
    precios: list[float] = []

    def anotar(prenda: Prenda, talla, color, peso: float) -> None:
        gustos["categoria"][prenda.categoria_id] += peso
        gustos["coleccion"][prenda.coleccion_id] += peso
        if prenda.marca:
            gustos["marca"][prenda.marca] += peso
        if color is not None:
            gustos["color"][color.nombre] += peso
        if talla is not None:
            tallas[talla.nombre] += peso

    for prenda, _v, talla, color, cantidad in _lineas_compradas(db, cliente_id):
        anotar(prenda, talla, color, PESO_SENAL["compra"] * min(cantidad, 3))
        compradas.add(prenda.id)
        precios.append(float(prenda.precio_venta))

    for prenda, _v, talla, color, cantidad in _lineas_reservadas(db, cliente_id):
        anotar(prenda, talla, color, PESO_SENAL["reserva"] * min(cantidad, 3))

    for prenda, veces in _prendas_vistas(db, cliente_id):
        anotar(prenda, None, None, PESO_SENAL["vista"] * min(veces, 5))

    return {
        "gustos": {clave: dict(valor) for clave, valor in gustos.items()},
        "tallas": dict(tallas),
        "talla_habitual": max(tallas, key=tallas.get) if tallas else None,
        "prendas_compradas": compradas,
        "precio_medio": sum(precios) / len(precios) if precios else None,
        "senales": len(compradas) + len(tallas),
    }


# ================================================================ popularidad
def popularidad(db: Session) -> dict[int, float]:
    """Unidades vendidas por prenda en los ultimos DIAS_POPULARIDAD, de 0 a 1."""
    desde = hoy_bolivia() - timedelta(days=DIAS_POPULARIDAD)
    filas = (
        db.query(Variante.prenda_id, func.sum(DetalleVenta.cantidad))
        .join(DetalleVenta, DetalleVenta.variante_id == Variante.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(Venta.estado == "pagada", Venta.fecha >= desde)
        .group_by(Variante.prenda_id)
        .all()
    )
    if not filas:
        return {}
    techo = max(float(total or 0) for _p, total in filas) or 1.0
    return {prenda_id: float(total or 0) / techo for prenda_id, total in filas}


# ================================================================== puntuacion
def _cercania_precio(precio: float, medio: float | None) -> float:
    """1.0 si gasta justo eso, y baja a 0 a medida que se aleja.

    Se mide en proporcion y no en bolivianos: alejarse Bs 100 no es lo mismo
    para quien compra de Bs 80 que para quien compra de Bs 600.
    """
    if not medio:
        return 0.0
    distancia = abs(precio - medio) / max(medio, 1.0)
    return max(0.0, 1.0 - distancia)


def _puntuar(item: dict, perfil_cliente: dict, populares: dict[int, float]) -> tuple[float, str]:
    """Puntaje de una prenda y el motivo que mas peso tuvo."""
    gustos = perfil_cliente["gustos"]
    aportes: list[tuple[float, str]] = []

    def sumar(clave: str, valor, texto: str) -> None:
        crudo = gustos[clave].get(valor, 0.0)
        if crudo <= 0:
            return
        # El gusto se normaliza contra el mas fuerte de su propia familia, para
        # que "categoria" y "marca" se puedan comparar entre si.
        techo = max(gustos[clave].values())
        aportes.append((PESOS[clave] * (crudo / techo), texto))

    categoria = (item.get("categoria") or "esta categoría").lower()
    sumar("categoria", item["categoria_id"], f"porque solés comprar {categoria}")
    sumar("coleccion", item["coleccion_id"], "porque es de una colección que ya elegiste")
    if item.get("marca"):
        sumar("marca", item["marca"], f"porque te gusta {item['marca']}")

    # El color no esta en la prenda sino en sus variantes: vale el mejor.
    colores = {v["color"] for v in item.get("variantes", [])}
    if gustos["color"] and colores:
        techo = max(gustos["color"].values())
        mejor = max(((gustos["color"].get(c, 0.0), c) for c in colores), default=(0.0, None))
        if mejor[0] > 0:
            aportes.append((PESOS["color"] * (mejor[0] / techo), f"porque solés elegir {mejor[1].lower()}"))

    cercania = _cercania_precio(float(item["precio_final"]), perfil_cliente["precio_medio"])
    if cercania > 0.35:
        aportes.append((PESOS["precio"] * cercania, "porque está en el precio que solés gastar"))

    fama = populares.get(item["id"], 0.0)
    if fama > 0:
        aportes.append((PESOS["popularidad"] * fama, "porque es de lo más vendido ahora"))

    puntaje = sum(peso for peso, _ in aportes)
    if item.get("promocion"):
        puntaje += BONUS_PROMOCION
        aportes.append((BONUS_PROMOCION, f"y está en promoción: {item['promocion']['etiqueta']}"))

    talla = perfil_cliente.get("talla_habitual")
    if talla and any(v["talla"] == talla and (v.get("disponible_total") or 0) > 0
                     for v in item.get("variantes", [])):
        puntaje += BONUS_TALLA
        aportes.append((BONUS_TALLA, f"y hay stock en tu talla {talla}"))

    if not aportes:
        return 0.0, "novedad del catálogo"
    return puntaje, max(aportes)[1]


# =================================================================== la salida
def recomendar(db: Session, cliente: Cliente | None, *, sucursal_id: int | None = None,
               limite: int = 8, excluir_compradas: bool = True) -> dict:
    """Prendas sugeridas para un cliente, con el motivo de cada una.

    Cada item tiene la misma forma que los de `GET /api/catalogo` (asi la web y
    la app movil reusan el modelo que ya tienen) y agrega `motivo` y `puntaje`.
    """
    items_catalogo = catalogo(db, sucursal_id=sucursal_id)
    if not items_catalogo:
        return {"estrategia": "sin_catalogo", "personalizada": False, "items": []}

    # Sin cliente o sin historial no hay a quien parecerse: se ofrece lo que
    # anda bien. Es el "arranque en frio", y conviene decirlo explicitamente.
    perfil_cliente = perfil(db, cliente.id) if cliente else None
    if perfil_cliente is None or perfil_cliente["senales"] == 0:
        return _mas_vendidas(db, items_catalogo, limite)

    populares = popularidad(db)
    puntuadas = []
    for item in items_catalogo:
        if excluir_compradas and item["id"] in perfil_cliente["prendas_compradas"]:
            continue
        puntaje, motivo = _puntuar(item, perfil_cliente, populares)
        if puntaje > 0:
            puntuadas.append({**item, "puntaje": round(puntaje, 2), "motivo": motivo})

    puntuadas.sort(key=lambda i: (-i["puntaje"], i["nombre"]))
    if not puntuadas:
        return _mas_vendidas(db, items_catalogo, limite)

    return {
        "estrategia": "perfil",
        "personalizada": True,
        "talla_habitual": perfil_cliente["talla_habitual"],
        "items": puntuadas[:limite],
    }


def _mas_vendidas(db: Session, catalogo: list[dict], limite: int) -> dict:
    """Arranque en frio: lo mas vendido, y las promociones adelante."""
    populares = populares_o_vacio = popularidad(db)
    orden = []
    for item in catalogo:
        puntaje = populares.get(item["id"], 0.0) + (0.5 if item.get("promocion") else 0.0)
        motivo = ("está en promoción" if item.get("promocion")
                  else "es de lo más vendido" if populares_o_vacio.get(item["id"])
                  else "novedad del catálogo")
        orden.append({**item, "puntaje": round(puntaje, 2), "motivo": motivo})
    orden.sort(key=lambda i: (-i["puntaje"], i["nombre"]))
    return {"estrategia": "populares", "personalizada": False, "items": orden[:limite]}


def registrar(db: Session, cliente: Cliente | None, resultado: dict) -> None:
    """Deja constancia de lo recomendado, para poder medirlo despues (CU28).

    Sirve para el reporte del administrador: que se recomendo, que se compro, y
    por lo tanto si el recomendador acierta.
    """
    if cliente is None or not resultado["items"]:
        return
    for item in resultado["items"]:
        db.add(Recomendacion(
            cliente_id=cliente.id, prenda_id=item["id"], motivo=(item.get("motivo") or "")[:200],
            puntaje=Decimal(str(item.get("puntaje") or 0)),
        ))
    db.commit()


def efectividad(db: Session, dias: int = 30) -> dict:
    """Para el administrador: de lo que se recomendo, cuanto termino vendido."""
    desde = hoy_bolivia() - timedelta(days=dias)
    recomendadas = (
        db.query(Recomendacion.cliente_id, Recomendacion.prenda_id)
        .filter(Recomendacion.fecha >= desde).distinct().all()
    )
    if not recomendadas:
        return {"dias": dias, "recomendaciones": 0, "compradas": 0, "efectividad": 0.0,
                "detalle": "Todavia no hay recomendaciones registradas en el periodo"}

    compradas = {
        (cliente_id, prenda_id)
        for cliente_id, prenda_id in (
            db.query(Venta.cliente_id, Variante.prenda_id)
            .join(DetalleVenta, DetalleVenta.venta_id == Venta.id)
            .join(Variante, Variante.id == DetalleVenta.variante_id)
            .filter(Venta.estado == "pagada", Venta.fecha >= desde).distinct().all()
        )
    }
    aciertos = sum(1 for par in recomendadas if par in compradas)
    return {
        "dias": dias,
        "recomendaciones": len(recomendadas),
        "compradas": aciertos,
        "efectividad": round(100 * aciertos / len(recomendadas), 1),
    }
