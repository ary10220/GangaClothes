"""Lo que el asistente puede consultar (CU28).

El modelo de lenguaje **no busca y no calcula**: pide. Cada funcion de aqui es
una consulta a nuestra propia base, y lo unico que el modelo recibe es el
resultado. De ahi salen las dos propiedades que nos importan:

* **No puede inventar.** Si una prenda no aparece en lo que devolvio
  `buscar_prendas`, el modelo no la tiene y no puede ofrecerla. Un asistente
  que recibe el catalogo entero y elige solo termina recomendando cosas que no
  existen o contradiciendose.
* **Siempre esta al dia.** Se consulta la base en cada llamada, no una copia.
  Una prenda que se publica ahora aparece en la respuesta siguiente, y una que
  se queda sin stock desaparece sola.

Cada rol ve su propia caja de herramientas: el cliente no puede pedir el
reporte de margenes y el personal no tiene "mis compras". Eso se resuelve con
los permisos que ya existen (`reportes:ver`), no con una lista aparte.

En esta version el asistente **solo consulta**: no agrega al carrito ni crea
reservas. Cuando se quiera dar ese paso, se agregan aqui las herramientas que
escriben y se marcan como tales, para poder pedir confirmacion antes.
"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.fechas import hoy_bolivia, texto_bolivia
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal
from app.models.ventas import Promocion, Venta
from app.modules.ia import recomendador
from app.modules.promociones import service as promociones
from app.modules.reportes import service as reportes
from app.modules.reservas import service as reservas_srv
from app.modules.ventas import service as ventas_srv

# Cuantos resultados se le pasan al modelo. Mas que esto no mejora la respuesta
# y si hace la llamada mas lenta y cara en tokens.
TOPE_RESULTADOS = 12
TOPE_LISTAS = 8


# ============================================================ forma compacta
def _prenda_breve(item: dict) -> dict:
    """Lo justo para que el asistente pueda hablar de una prenda."""
    breve = {
        "id": item["id"],
        "nombre": item["nombre"],
        "categoria": item.get("categoria"),
        "marca": item.get("marca"),
        "precio": float(item["precio_final"]),
        "colores_disponibles": item.get("colores") or [],
        "tallas_disponibles": item.get("tallas") or [],
        "unidades_disponibles": item.get("disponible_total") or 0,
    }
    if item.get("promocion"):
        breve["promocion"] = item["promocion"]["nombre"]
        breve["precio_sin_promocion"] = float(item["precio_venta"])
    if item.get("motivo"):
        breve["por_que_se_sugiere"] = item["motivo"]
    return breve


def _respuesta(items: list[dict], total: int | None = None, **extra) -> dict:
    """Resultado uniforme. `total` avisa al modelo que hay mas de lo que ve, para
    que ofrezca afinar la busqueda en vez de afirmar que eso es todo."""
    salida = {"cantidad": len(items), "resultados": items, **extra}
    if total is not None and total > len(items):
        salida["hay_mas"] = total - len(items)
    return salida


def _coincide(texto: str | None, valor: str | None) -> bool:
    return bool(texto) and bool(valor) and texto.lower().strip() in valor.lower()


# ============================================================ herramientas del cliente
def buscar_prendas(db: Session, ctx: dict, *, texto: str | None = None,
                   categoria: str | None = None, color: str | None = None,
                   talla: str | None = None, marca: str | None = None,
                   precio_max: float | None = None, precio_min: float | None = None,
                   solo_promociones: bool = False) -> dict:
    """Busca en el catalogo publicado. Solo devuelve prendas con stock real."""
    items = recomendador.catalogo(db, sucursal_id=ctx.get("sucursal_id"))
    filtrados = []
    for item in items:
        if texto and not (_coincide(texto, item["nombre"]) or _coincide(texto, item.get("descripcion"))
                          or _coincide(texto, item.get("categoria")) or _coincide(texto, item.get("marca"))):
            continue
        if categoria and not _coincide(categoria, item.get("categoria")):
            continue
        if marca and not _coincide(marca, item.get("marca")):
            continue
        # Color y talla se miran contra las variantes CON stock: de nada sirve
        # que exista el rojo si no queda ninguna unidad roja.
        if color and not any(_coincide(color, c) for c in item.get("colores") or []):
            continue
        if talla and talla.upper().strip() not in [t.upper() for t in item.get("tallas") or []]:
            continue
        precio = float(item["precio_final"])
        if precio_max is not None and precio > precio_max:
            continue
        if precio_min is not None and precio < precio_min:
            continue
        if solo_promociones and not item.get("promocion"):
            continue
        filtrados.append(item)

    filtrados.sort(key=lambda i: float(i["precio_final"]))
    pedido = {k: v for k, v in dict(texto=texto, categoria=categoria, color=color, talla=talla,
                                    marca=marca, precio_max=precio_max, precio_min=precio_min).items()
              if v is not None}
    if not filtrados:
        # Se le dice al modelo QUE hay, para que pueda ofrecer una alternativa
        # en vez de quedarse en "no tengo".
        return {
            "cantidad": 0, "resultados": [], "busqueda": pedido,
            "aviso": "No hay ninguna prenda publicada que cumpla con todo lo pedido.",
            "categorias_del_catalogo": sorted({i["categoria"] for i in items if i.get("categoria")}),
            "colores_con_stock": sorted({c for i in items for c in (i.get("colores") or [])}),
        }
    return _respuesta([_prenda_breve(i) for i in filtrados[:TOPE_RESULTADOS]],
                      total=len(filtrados), busqueda=pedido)


def recomendar_para_mi(db: Session, ctx: dict, *, limite: int = 6) -> dict:
    """Sugerencias del recomendador propio, con el motivo de cada una."""
    cliente = ctx.get("cliente")
    resultado = recomendador.recomendar(
        db, cliente, sucursal_id=ctx.get("sucursal_id"), limite=min(limite, TOPE_RESULTADOS)
    )
    if cliente is not None:
        recomendador.registrar(db, cliente, resultado)
    return _respuesta(
        [_prenda_breve(i) for i in resultado["items"]],
        personalizada=resultado["personalizada"],
        criterio=("Segun lo que este cliente compro, reservo y miro"
                  if resultado["personalizada"]
                  else "Todavia no hay historial suficiente: son las mas vendidas y las que estan en promocion"),
        talla_habitual=resultado.get("talla_habitual"),
    )


def ver_prenda(db: Session, ctx: dict, *, nombre: str) -> dict:
    """Ficha de una prenda: precio, colores, tallas y en que sucursal hay."""
    items = recomendador.catalogo(db)
    encontrados = [i for i in items if _coincide(nombre, i["nombre"])]
    if not encontrados:
        return {"encontrada": False,
                "aviso": f"No hay ninguna prenda publicada que se llame '{nombre}'.",
                "prendas_del_catalogo": [i["nombre"] for i in items[:TOPE_RESULTADOS]]}

    item = encontrados[0]
    por_sucursal: dict[str, int] = {}
    for variante in item["variantes"]:
        for fila in variante.get("disponibilidad") or []:
            if fila["disponible"] > 0:
                por_sucursal[fila["sucursal"]] = por_sucursal.get(fila["sucursal"], 0) + fila["disponible"]
    return {
        "encontrada": True,
        **_prenda_breve(item),
        "descripcion": item.get("descripcion"),
        "temporada": item.get("temporada"),
        "coleccion": item.get("coleccion"),
        "disponible_por_sucursal": por_sucursal,
        "combinaciones": [
            {"talla": v["talla"], "color": v["color"], "disponibles": v.get("disponible_total") or 0}
            for v in item["variantes"] if (v.get("disponible_total") or 0) > 0
        ][:TOPE_RESULTADOS],
    }


def promociones_vigentes(db: Session, ctx: dict) -> dict:
    """Las promociones que rigen hoy y sobre que prendas."""
    hoy = hoy_bolivia()
    activas = (
        db.query(Promocion)
        .filter(Promocion.activo == True)  # noqa: E712
        .filter((Promocion.fecha_inicio == None) | (Promocion.fecha_inicio <= hoy))  # noqa: E711
        .filter((Promocion.fecha_fin == None) | (Promocion.fecha_fin >= hoy))  # noqa: E711
        .all()
    )
    if not activas:
        return {"cantidad": 0, "resultados": [], "aviso": "Hoy no hay ninguna promocion vigente."}

    items = recomendador.catalogo(db, sucursal_id=ctx.get("sucursal_id"))
    por_promo: dict[int, list[str]] = {}
    for item in items:
        if item.get("promocion"):
            por_promo.setdefault(item["promocion"]["id"], []).append(item["nombre"])

    return _respuesta([{
        "nombre": p.nombre,
        "descuento": promociones.etiqueta(p),
        "hasta": p.fecha_fin.strftime("%d/%m/%Y") if p.fecha_fin else "sin fecha de fin",
        "prendas": por_promo.get(p.id, [])[:TOPE_LISTAS],
    } for p in activas])


def mis_compras(db: Session, ctx: dict, *, limite: int = 5) -> dict:
    """Las ultimas compras pagadas de este cliente."""
    cliente = ctx.get("cliente")
    if cliente is None:
        return {"cantidad": 0, "resultados": [], "aviso": "Esta cuenta no es de un cliente."}
    compras = (
        db.query(Venta).filter(Venta.cliente_id == cliente.id, Venta.estado == "pagada")
        .order_by(Venta.fecha.desc()).limit(min(limite, TOPE_LISTAS)).all()
    )
    return _respuesta([{
        "comprobante": v.nro_comprobante,
        "fecha": texto_bolivia(v.fecha.isoformat() + "Z" if v.fecha else None, con_hora=False),
        "total": float(ventas_srv.dinero(v.total)),
        "prendas": [f"{d['prenda']} {d['talla']}/{d['color']} x{d['cantidad']}"
                    for d in ventas_srv.salida(db, v)["detalle"]],
    } for v in compras])


def mis_reservas(db: Session, ctx: dict) -> dict:
    """Reservas del cliente para probarse prendas en tienda."""
    cliente = ctx.get("cliente")
    if cliente is None:
        return {"cantidad": 0, "resultados": [], "aviso": "Esta cuenta no es de un cliente."}
    filas = reservas_srv.mias(db, ctx["usuario"])
    return _respuesta([{
        "id": r.get("id"), "estado": r.get("estado"), "sucursal": r.get("sucursal"),
        "fecha_de_prueba": r.get("fecha_hora_prueba"),
        "prendas": [f"{d.get('prenda')} {d.get('talla')}/{d.get('color')}"
                    for d in (r.get("detalle") or [])],
    } for r in filas[:TOPE_LISTAS]], total=len(filas))


# ============================================================ herramientas del personal
def _rango(desde: str | None, hasta: str | None, dias_por_defecto: int = 30) -> tuple[date, date]:
    """Convierte las fechas que mande el modelo. Si no manda, ultimos 30 dias."""
    def leer(texto: str | None) -> date | None:
        if not texto:
            return None
        try:
            return datetime.strptime(texto[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    fin = leer(hasta) or hoy_bolivia()
    inicio = leer(desde) or (fin - timedelta(days=dias_por_defecto))
    return inicio, fin


def _sucursal_por_nombre(db: Session, nombre: str | None) -> int | None:
    if not nombre:
        return None
    sucursal = next((s for s in db.query(Sucursal).all() if _coincide(nombre, s.nombre)), None)
    return sucursal.id if sucursal else None


def reporte_ventas(db: Session, ctx: dict, *, desde: str | None = None, hasta: str | None = None,
                   sucursal: str | None = None, canal: str | None = None,
                   agrupar: str = "dia") -> dict:
    """Ventas del periodo: totales, y el desglose por sucursal y canal."""
    inicio, fin = _rango(desde, hasta)
    datos = reportes.ventas(db, inicio, fin, _sucursal_por_nombre(db, sucursal), canal, agrupar)
    # Se recorta la lista de ventas una por una: al modelo le sirven los totales.
    return {
        "periodo": datos["periodo"],
        "totales": datos["totales"],
        "por_sucursal": datos["por_sucursal"][:TOPE_LISTAS],
        "por_canal": datos["por_canal"],
        "por_periodo": datos["por_periodo"][-TOPE_RESULTADOS:],
        "nota": "Importes en bolivianos. Solo ventas pagadas.",
    }


def reporte_inventario(db: Session, ctx: dict, *, sucursal: str | None = None) -> dict:
    """Stock valorizado de hoy y los movimientos recientes."""
    datos = reportes.inventario(db, None, None, _sucursal_por_nombre(db, sucursal))
    return {
        "totales": datos["totales"],
        "por_sucursal": datos["por_sucursal"][:TOPE_LISTAS],
        "movimientos_por_tipo": datos["movimientos_por_tipo"],
        "nota": "El stock es la foto de hoy; los movimientos son del periodo.",
    }


def reporte_margen(db: Session, ctx: dict, *, desde: str | None = None, hasta: str | None = None,
                   sucursal: str | None = None) -> dict:
    """Ganancia por prenda: precio de venta menos costo."""
    inicio, fin = _rango(desde, hasta)
    datos = reportes.margen(db, inicio, fin, _sucursal_por_nombre(db, sucursal))
    prendas = sorted(datos["prendas"], key=lambda p: -(p.get("ganancia_realizada") or 0))
    return {
        "periodo": datos["periodo"],
        "resumen": datos["resumen"],
        "mas_rentables": prendas[:TOPE_LISTAS],
        "menos_rentables": prendas[-3:] if len(prendas) > TOPE_LISTAS else [],
    }


def resumen_del_negocio(db: Session, ctx: dict, *, desde: str | None = None,
                        hasta: str | None = None, sucursal: str | None = None) -> dict:
    """Los indicadores principales, como en el panel: ventas, variacion y top."""
    inicio, fin = _rango(desde, hasta)
    datos = reportes.dashboard(db, inicio, fin, _sucursal_por_nombre(db, sucursal))
    return {
        "periodo": datos["periodo"],
        "indicadores": datos["indicadores"],
        "por_canal": datos["por_canal"],
        "por_sucursal": datos["por_sucursal"][:TOPE_LISTAS],
        "por_categoria": datos["por_categoria"][:TOPE_LISTAS],
        "top_prendas": datos["top_prendas"][:TOPE_LISTAS],
        "metodos_pago": datos["metodos_pago"],
        "reservas_por_estado": datos["reservas_por_estado"],
    }


def stock_bajo(db: Session, ctx: dict, *, sucursal: str | None = None) -> dict:
    """Variantes por debajo de su stock minimo: lo que habria que reponer."""
    sucursal_id = _sucursal_por_nombre(db, sucursal)
    consulta = db.query(Inventario).filter(
        Inventario.cantidad - Inventario.cantidad_reservada <= Inventario.stock_minimo
    )
    if sucursal_id:
        consulta = consulta.filter(Inventario.sucursal_id == sucursal_id)
    filas = consulta.all()
    if not filas:
        return {"cantidad": 0, "resultados": [], "aviso": "Ninguna variante esta por debajo de su minimo."}

    sucursales = {s.id: s.nombre for s in db.query(Sucursal).all()}
    detalle = []
    for i in filas:
        fila = ventas_srv._variante(db, i.variante_id)
        if fila is None:
            continue
        variante, prenda, talla, color = fila
        detalle.append({
            "prenda": prenda.nombre, "talla": talla.nombre, "color": color.nombre,
            "sku": variante.sku, "sucursal": sucursales.get(i.sucursal_id),
            "disponible": i.cantidad - i.cantidad_reservada, "minimo": i.stock_minimo,
            "faltan": max(0, (i.stock_maximo or i.stock_minimo) - i.cantidad),
        })
    detalle.sort(key=lambda d: d["disponible"])
    return _respuesta(detalle[:TOPE_RESULTADOS], total=len(detalle))


def efectividad_recomendaciones(db: Session, ctx: dict, *, dias: int = 30) -> dict:
    """Cuanto de lo que el recomendador sugirio termino comprandose."""
    return recomendador.efectividad(db, dias)


# ============================================================ catalogo de herramientas
def _texto(descripcion: str) -> dict:
    return {"type": "string", "description": descripcion}


def _numero(descripcion: str) -> dict:
    return {"type": "number", "description": descripcion}


CLIENTE = {
    "buscar_prendas": {
        "fn": buscar_prendas,
        "descripcion": ("Busca prendas del catalogo con stock real. Usala SIEMPRE que "
                        "el cliente pregunte por una prenda, un color, una talla o un precio. "
                        "Nunca nombres una prenda que no haya salido de aqui."),
        "parametros": {
            "texto": _texto("Palabra suelta: nombre, categoria o marca"),
            "categoria": _texto("Vestidos, Poleras, Pantalones, Camisas, Faldas, Chamarras..."),
            "color": _texto("Color pedido, por ejemplo rojo o negro"),
            "talla": _texto("Talla pedida: XS, S, M, L, XL"),
            "marca": _texto("Marca pedida"),
            "precio_max": _numero("Precio maximo en bolivianos"),
            "precio_min": _numero("Precio minimo en bolivianos"),
            "solo_promociones": {"type": "boolean", "description": "Solo lo que esta rebajado"},
        },
    },
    "recomendar_para_mi": {
        "fn": recomendar_para_mi,
        "descripcion": ("Pide al recomendador de la tienda que sugiera prendas para ESTE cliente, "
                        "segun lo que compro, reservo y miro. Usala cuando pida recomendaciones, "
                        "ideas o no sepa que llevar."),
        "parametros": {"limite": _numero("Cuantas sugerencias, entre 3 y 10")},
    },
    "ver_prenda": {
        "fn": ver_prenda,
        "descripcion": ("Ficha completa de una prenda: descripcion, tallas, colores y en que "
                        "sucursal hay unidades. Usala cuando pregunten por una prenda concreta."),
        "parametros": {"nombre": _texto("Nombre de la prenda, tal como aparecio en la busqueda")},
        "requeridos": ["nombre"],
    },
    "promociones_vigentes": {
        "fn": promociones_vigentes,
        "descripcion": "Promociones que rigen hoy y sobre que prendas se aplican.",
        "parametros": {},
    },
    "mis_compras": {
        "fn": mis_compras,
        "descripcion": "Ultimas compras pagadas de este cliente, con su comprobante.",
        "parametros": {"limite": _numero("Cuantas compras, hasta 8")},
    },
    "mis_reservas": {
        "fn": mis_reservas,
        "descripcion": "Reservas del cliente para probarse prendas en la tienda.",
        "parametros": {},
    },
}

PERSONAL = {
    "resumen_del_negocio": {
        "fn": resumen_del_negocio,
        "descripcion": ("Indicadores del periodo: total vendido, cantidad de ventas, ticket "
                        "promedio, variacion contra el periodo anterior, y el desglose por canal, "
                        "sucursal y categoria. Es la herramienta general: empeza por esta."),
        "parametros": {
            "desde": _texto("Fecha inicial en formato AAAA-MM-DD"),
            "hasta": _texto("Fecha final en formato AAAA-MM-DD"),
            "sucursal": _texto("Nombre de la sucursal, si se pregunta por una sola"),
        },
    },
    "reporte_ventas": {
        "fn": reporte_ventas,
        "descripcion": "Ventas del periodo agrupadas por dia, semana o mes, con corte por sucursal y canal.",
        "parametros": {
            "desde": _texto("Fecha inicial AAAA-MM-DD"),
            "hasta": _texto("Fecha final AAAA-MM-DD"),
            "sucursal": _texto("Nombre de la sucursal"),
            "canal": _texto("web, movil o caja"),
            "agrupar": _texto("dia, semana o mes"),
        },
    },
    "reporte_margen": {
        "fn": reporte_margen,
        "descripcion": "Ganancia por prenda (precio de venta menos costo): las mas y las menos rentables.",
        "parametros": {
            "desde": _texto("Fecha inicial AAAA-MM-DD"),
            "hasta": _texto("Fecha final AAAA-MM-DD"),
            "sucursal": _texto("Nombre de la sucursal"),
        },
    },
    "reporte_inventario": {
        "fn": reporte_inventario,
        "descripcion": "Stock valorizado de hoy por sucursal y los movimientos recientes.",
        "parametros": {"sucursal": _texto("Nombre de la sucursal")},
    },
    "stock_bajo": {
        "fn": stock_bajo,
        "descripcion": ("Variantes por debajo de su stock minimo, con cuantas unidades faltan "
                        "para llegar al maximo. Es lo que hay que reponer."),
        "parametros": {"sucursal": _texto("Nombre de la sucursal")},
    },
    "efectividad_recomendaciones": {
        "fn": efectividad_recomendaciones,
        "descripcion": "Que porcentaje de lo que el recomendador sugirio termino comprandose.",
        "parametros": {"dias": _numero("Ventana en dias, por defecto 30")},
    },
}


def disponibles(personal: bool, es_cliente: bool) -> dict:
    """Las herramientas que le corresponden a quien esta conversando."""
    caja = {}
    if es_cliente:
        caja.update(CLIENTE)
    if personal:
        # El personal tambien busca en el catalogo, pero no tiene "mis compras".
        caja.update({k: v for k, v in CLIENTE.items()
                     if k in ("buscar_prendas", "ver_prenda", "promociones_vigentes")})
        caja.update(PERSONAL)
    return caja


def declaraciones(caja: dict) -> list[dict]:
    """Las herramientas descritas como las espera la API de Gemini."""
    return [{
        "name": nombre,
        "description": h["descripcion"],
        "parameters": {
            "type": "object",
            "properties": h["parametros"],
            "required": h.get("requeridos", []),
        },
    } for nombre, h in caja.items()]


def ejecutar(db: Session, ctx: dict, caja: dict, nombre: str, argumentos: dict) -> dict:
    """Corre una herramienta. Un error nunca corta la conversacion: vuelve como
    un dato mas para que el asistente lo cuente con sus palabras."""
    herramienta = caja.get(nombre)
    if herramienta is None:
        return {"error": f"La herramienta '{nombre}' no existe o no esta disponible para este usuario"}
    permitidos = set(herramienta["parametros"])
    limpios = {k: v for k, v in (argumentos or {}).items() if k in permitidos and v is not None}
    try:
        return herramienta["fn"](db, ctx, **limpios)
    except Exception as e:  # noqa: BLE001
        db.rollback()
        return {"error": f"No se pudo completar la consulta: {e}"}
