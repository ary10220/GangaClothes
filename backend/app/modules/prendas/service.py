"""Prendas: variantes con su stock inicial, publicacion y catalogo.

Una prenda tiene dos banderas independientes:

- activo: existe en el sistema. En false esta archivada y no se vende por ningun canal.
- publicado: se muestra en la tienda en linea (web y movil). Nace en false.

La tienda en linea (catalogo publico, reservas y carrito) solo trabaja con
prendas activas y publicadas. La caja y las compras trabajan con toda prenda
activa, este publicada o no: una prenda puede venderse en tienda o reponerse
antes de salir en la web.
"""
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import to_dict
from app.models.catalogo import AssetAR, Coleccion, Color, Prenda, Talla, Variante
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal
from app.modules.inventario import service as inventario
from app.modules.promociones import service as promociones


# ------------------------------------------------------------ resumen stock
def resumen_stock(db: Session, prenda_ids: list[int] | None = None) -> dict[int, dict]:
    """Por prenda: variantes, unidades, disponibles y sucursales con unidades.

    Solo cuenta variantes activas en sucursales activas: es lo que se puede vender.
    """
    variantes = db.query(Variante.prenda_id, func.count(Variante.id)).filter(Variante.activo.isnot(False))
    stock = (
        db.query(
            Variante.prenda_id,
            func.coalesce(func.sum(Inventario.cantidad), 0),
            func.coalesce(func.sum(Inventario.cantidad - Inventario.cantidad_reservada), 0),
            func.count(func.distinct(case((Inventario.cantidad > 0, Inventario.sucursal_id)))),
        )
        .join(Inventario, Inventario.variante_id == Variante.id)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .filter(Variante.activo.isnot(False), Sucursal.activo.isnot(False))
    )
    if prenda_ids is not None:
        variantes = variantes.filter(Variante.prenda_id.in_(prenda_ids))
        stock = stock.filter(Variante.prenda_id.in_(prenda_ids))

    salida: dict[int, dict] = defaultdict(
        lambda: {"variantes": 0, "stock_total": 0, "disponible_total": 0, "sucursales_con_stock": 0}
    )
    for prenda_id, cuantas in variantes.group_by(Variante.prenda_id).all():
        salida[prenda_id]["variantes"] = cuantas
    for prenda_id, total, disponible, sucursales in stock.group_by(Variante.prenda_id).all():
        salida[prenda_id].update(stock_total=int(total), disponible_total=int(disponible),
                                 sucursales_con_stock=int(sucursales))
    return salida


def prenda_salida(db: Session, prenda: Prenda, resumen: dict | None = None) -> dict:
    datos = resumen if resumen is not None else resumen_stock(db, [prenda.id])[prenda.id]
    return {**to_dict(prenda), "publicado": bool(prenda.publicado), **datos}


def listar(db: Session) -> list[dict]:
    prendas = db.query(Prenda).order_by(Prenda.id).all()
    resumen = resumen_stock(db)
    return [prenda_salida(db, p, resumen[p.id]) for p in prendas]


def _prenda(db: Session, prenda_id: int) -> Prenda:
    prenda = db.get(Prenda, prenda_id)
    if prenda is None:
        raise HTTPException(404, "Prenda no encontrada")
    return prenda


# -------------------------------------------------------------- variantes
def variante_salida(db: Session, v: Variante) -> dict:
    talla = db.get(Talla, v.talla_id)
    color = db.get(Color, v.color_id)
    filas = (
        db.query(Inventario, Sucursal)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .filter(Inventario.variante_id == v.id)
        .order_by(Sucursal.nombre)
        .all()
    )
    stock = [{
        "inventario_id": inv.id,
        "sucursal_id": s.id,
        "sucursal": s.nombre,
        "sucursal_activa": s.activo is not False,
        "cantidad": inv.cantidad,
        "cantidad_reservada": inv.cantidad_reservada,
        "disponible": inv.cantidad - inv.cantidad_reservada,
        "stock_minimo": inv.stock_minimo or 0,
        "stock_maximo": inv.stock_maximo or 0,
    } for inv, s in filas]
    activas = [f for f in stock if f["sucursal_activa"]]
    assets = db.query(AssetAR).filter(AssetAR.variante_id == v.id).count()
    return {
        **to_dict(v),
        "talla": talla.nombre if talla else None,
        "color": color.nombre if color else None,
        "color_hex": color.codigo_hex if color else None,
        # El panel necesita saber si la variante ya tiene su recurso del probador (CU24).
        "assets_ar": assets,
        "tiene_asset_ar": assets > 0,
        "stock": stock,
        "stock_total": sum(f["cantidad"] for f in activas),
        "disponible_total": sum(f["disponible"] for f in activas),
    }


def variantes_de(db: Session, prenda_id: int) -> list[dict]:
    _prenda(db, prenda_id)
    filas = (
        db.query(Variante)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(Variante.prenda_id == prenda_id)
        .order_by(Talla.orden, Talla.nombre, Color.nombre)
        .all()
    )
    return [variante_salida(db, v) for v in filas]


def _nueva_variante(db: Session, prenda: Prenda, talla: Talla, color: Color,
                    imagen_url: str | None) -> Variante:
    v = Variante(prenda_id=prenda.id, talla_id=talla.id, color_id=color.id,
                 sku=f"P{prenda.id}-T{talla.id}-C{color.id}", imagen_url=imagen_url)
    db.add(v)
    db.flush()
    return v


def _prenda_editable(db: Session, prenda_id: int) -> Prenda:
    prenda = _prenda(db, prenda_id)
    if prenda.activo is False:
        raise HTTPException(400, f"'{prenda.nombre}' esta archivada: reactivala antes de agregarle variantes")
    return prenda


def _talla_y_color(db: Session, talla_id: int, color_id: int) -> tuple[Talla, Color]:
    talla, color = db.get(Talla, talla_id), db.get(Color, color_id)
    if talla is None:
        raise HTTPException(400, f"La talla {talla_id} no existe")
    if color is None:
        raise HTTPException(400, f"El color {color_id} no existe")
    return talla, color


def _confirmar(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        # Otra peticion creo la misma combinacion o el mismo stock a la vez.
        db.rollback()
        raise HTTPException(400, "La variante o su stock se registraron al mismo tiempo desde otra sesion. "
                                 "Recarga y revisa antes de repetir")


def crear_variante(db: Session, prenda_id: int, datos, usuario_id: int) -> tuple[dict, list]:
    prenda = _prenda_editable(db, prenda_id)
    talla, color = _talla_y_color(db, datos.talla_id, datos.color_id)
    existe = (
        db.query(Variante)
        .filter(Variante.prenda_id == prenda.id, Variante.talla_id == talla.id, Variante.color_id == color.id)
        .first()
    )
    if existe:
        raise HTTPException(400, f"Ya existe la variante talla {talla.nombre} color {color.nombre} ({existe.sku})")

    v = _nueva_variante(db, prenda, talla, color, datos.imagen_url)
    stock = inventario.abrir_stock_en_sucursales(db, v, datos.stock_inicial, usuario_id)
    _confirmar(db)
    return variante_salida(db, v), stock


def generar_variantes(db: Session, prenda_id: int, datos, usuario_id: int) -> dict:
    """Crea todas las combinaciones talla x color que falten, cada una con el
    mismo stock inicial por sucursal. Todo o nada."""
    prenda = _prenda_editable(db, prenda_id)
    talla_ids = list(dict.fromkeys(datos.talla_ids))
    color_ids = list(dict.fromkeys(datos.color_ids))
    if not talla_ids or not color_ids:
        raise HTTPException(400, "Elige al menos una talla y un color")

    existentes = {
        (v.talla_id, v.color_id): v
        for v in db.query(Variante).filter(Variante.prenda_id == prenda.id).all()
    }
    creadas, omitidas = [], []
    for talla_id in talla_ids:
        for color_id in color_ids:
            talla, color = _talla_y_color(db, talla_id, color_id)
            if (talla_id, color_id) in existentes:
                omitidas.append(f"{talla.nombre}/{color.nombre}")
                continue
            v = _nueva_variante(db, prenda, talla, color, datos.imagen_url)
            inventario.abrir_stock_en_sucursales(db, v, datos.stock_inicial, usuario_id)
            creadas.append(v)

    if not creadas:
        raise HTTPException(400, f"Esas combinaciones ya existen: {', '.join(omitidas)}")
    _confirmar(db)
    return {
        "creadas": [variante_salida(db, v) for v in creadas],
        "omitidas": omitidas,
        "prenda": prenda_salida(db, prenda),
    }


def cargar_stock_inicial(db: Session, variante_id: int, lineas, usuario_id: int) -> dict:
    """Stock inicial de una variante que ya existe, en sucursales donde aun no tiene."""
    v = db.get(Variante, variante_id)
    if v is None:
        raise HTTPException(404, "Variante no encontrada")
    _prenda_editable(db, v.prenda_id)
    if not lineas:
        raise HTTPException(400, "Indica al menos una sucursal")
    inventario.abrir_stock_en_sucursales(db, v, lineas, usuario_id)
    _confirmar(db)
    return variante_salida(db, v)


# ------------------------------------------------------------- publicacion
def publicar(db: Session, prenda_id: int, confirmar_sin_stock: bool) -> tuple[dict, bool]:
    """Devuelve la prenda y si se publico sin unidades disponibles."""
    prenda = _prenda(db, prenda_id)
    if prenda.activo is False:
        raise HTTPException(400, f"'{prenda.nombre}' esta archivada: reactivala antes de publicarla")

    resumen = resumen_stock(db, [prenda.id])[prenda.id]
    sin_stock = resumen["disponible_total"] <= 0
    if sin_stock and not confirmar_sin_stock:
        # 409: la peticion es valida pero pide una confirmacion explicita.
        motivo = ("no tiene variantes" if resumen["variantes"] == 0
                  else "no tiene unidades disponibles en ninguna sucursal")
        raise HTTPException(
            409,
            f"'{prenda.nombre}' {motivo}. Si la publicas, los clientes la veran agotada y no podran "
            "reservarla ni comprarla. Carga su stock o confirma que quieres publicarla igual",
        )
    prenda.publicado = True
    db.commit()
    return prenda_salida(db, prenda, resumen), sin_stock


def despublicar(db: Session, prenda_id: int) -> dict:
    prenda = _prenda(db, prenda_id)
    prenda.publicado = False
    db.commit()
    return prenda_salida(db, prenda)


def editar(db: Session, prenda_id: int, cambios: dict) -> dict:
    prenda = _prenda(db, prenda_id)
    for clave, valor in cambios.items():
        setattr(prenda, clave, valor)
    # Una prenda archivada no puede seguir en la tienda. Al reactivarla vuelve
    # sin publicar: publicarla es una decision aparte.
    if cambios.get("activo") is False:
        prenda.publicado = False
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Categoria o coleccion inexistente")
    db.refresh(prenda)
    return prenda_salida(db, prenda)


# ---------------------------------------------------------------- catalogo
def _recurso_ar(a: AssetAR) -> dict:
    return {"id": a.id, "tipo": a.tipo, "url_recurso": a.url_recurso, "escala": float(a.escala or 1)}


def recursos_ar_publicos(db: Session, variante_id: int) -> dict:
    """Recursos del probador de una variante que se vende en la tienda en linea."""
    fila = (
        db.query(Variante, Prenda)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .filter(Variante.id == variante_id)
        .first()
    )
    if fila is None or fila[0].activo is False or fila[1].activo is False or not fila[1].publicado:
        raise HTTPException(404, "La variante no existe o no esta a la venta en la tienda en linea")
    variante, prenda = fila
    recursos = db.query(AssetAR).filter(AssetAR.variante_id == variante.id).order_by(AssetAR.id).all()
    return {
        "variante_id": variante.id,
        "sku": variante.sku,
        "prenda": prenda.nombre,
        "tiene_probador": bool(recursos),
        "recursos_ar": [_recurso_ar(a) for a in recursos],
    }


def url_imagen(ruta: str | None) -> str | None:
    """Una ruta relativa del sitio web se completa con IMAGENES_BASE_URL, si esta
    definida (la app movil no tiene un dominio propio contra el cual resolverla)."""
    if ruta and ruta.startswith("/") and settings.imagenes_base_url:
        return settings.imagenes_base_url.rstrip("/") + ruta
    return ruta


def _precio_con_promocion(prenda: Prenda, promos) -> dict:
    """precio_venta es el precio de lista; precio_final, lo que paga el cliente hoy."""
    calculo = promociones.aplicar(prenda.precio_venta, promos)
    return {
        "precio_final": float(calculo["precio_final"]),
        "descuento": float(calculo["descuento"]),
        "promocion": promociones.resumen_publico(calculo["promocion"]),
    }


def armar_catalogo(db: Session, *, solo_publicadas: bool, q: str | None = None,
                   categoria_id: int | None = None, temporada_id: int | None = None,
                   coleccion_id: int | None = None, talla_id: int | None = None,
                   color_id: int | None = None, sucursal_id: int | None = None) -> list[dict]:
    """Prendas activas con sus variantes y lo disponible en cada sucursal.

    - solo_publicadas: el catalogo publico. Sin esa marca lo usan caja y compras.
    - sucursal_id: la disponibilidad se limita a esa sucursal y, en el catalogo
      publico, quedan solo las prendas que tienen unidades disponibles ahi.
    """
    if sucursal_id is not None:
        sucursal = db.get(Sucursal, sucursal_id)
        if sucursal is None or sucursal.activo is False:
            raise HTTPException(404, "La sucursal no existe o no esta activa")

    consulta = db.query(Prenda).filter(Prenda.activo == True)  # noqa: E712
    if solo_publicadas:
        consulta = consulta.filter(Prenda.publicado == True)  # noqa: E712
    if q:
        consulta = consulta.filter(Prenda.nombre.ilike(f"%{q}%"))
    if categoria_id:
        consulta = consulta.filter(Prenda.categoria_id == categoria_id)
    if coleccion_id:
        consulta = consulta.filter(Prenda.coleccion_id == coleccion_id)
    if temporada_id:
        consulta = consulta.join(Coleccion, Prenda.coleccion_id == Coleccion.id) \
                           .filter(Coleccion.temporada_id == temporada_id)
    prendas = consulta.order_by(Prenda.nombre, Prenda.id).all()
    if not prendas:
        return []

    # Tres consultas en total, no una por variante.
    vq = (
        db.query(Variante, Talla, Color)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(Variante.prenda_id.in_([p.id for p in prendas]), Variante.activo == True)  # noqa: E712
    )
    if talla_id:
        vq = vq.filter(Variante.talla_id == talla_id)
    if color_id:
        vq = vq.filter(Variante.color_id == color_id)
    variantes = vq.order_by(Talla.orden, Talla.nombre, Color.nombre).all()

    # Recursos del probador virtual (PNG transparente) de cada variante: la app
    # movil los necesita para superponer la prenda sobre la camara.
    recursos = defaultdict(list)
    for a in (db.query(AssetAR)
              .filter(AssetAR.variante_id.in_([v.id for v, _t, _c in variantes] or [0]))
              .order_by(AssetAR.id).all()):
        recursos[a.variante_id].append(_recurso_ar(a))

    iq = (
        db.query(Inventario, Sucursal)
        .join(Sucursal, Sucursal.id == Inventario.sucursal_id)
        .filter(Inventario.variante_id.in_([v.id for v, _t, _c in variantes] or [0]),
                Sucursal.activo.isnot(False))
    )
    if sucursal_id is not None:
        iq = iq.filter(Inventario.sucursal_id == sucursal_id)
    stock = defaultdict(list)
    for inv, s in iq.order_by(Sucursal.nombre).all():
        stock[inv.variante_id].append({"sucursal_id": s.id, "sucursal": s.nombre,
                                       "disponible": inv.cantidad - inv.cantidad_reservada})

    por_prenda = defaultdict(list)
    for v, talla, color in variantes:
        disponibilidad = stock[v.id]
        por_prenda[v.prenda_id].append({
            "id": v.id, "sku": v.sku,
            "talla_id": talla.id, "talla": talla.nombre,
            "color_id": color.id, "color": color.nombre, "color_hex": color.codigo_hex,
            "imagen_url": url_imagen(v.imagen_url),
            "disponible_total": sum(max(d["disponible"], 0) for d in disponibilidad),
            "disponibilidad": disponibilidad,
            "tiene_probador": bool(recursos[v.id]),
            "recursos_ar": recursos[v.id],
        })

    # CU18: el precio con descuento sale siempre del modulo de promociones.
    vigentes = promociones.vigentes_por_prenda(db, [p.id for p in prendas])

    resultado = []
    for p in prendas:
        lista = por_prenda[p.id]
        if (talla_id or color_id) and not lista:
            continue
        disponible = sum(v["disponible_total"] for v in lista)
        if solo_publicadas and sucursal_id is not None and disponible <= 0:
            continue
        resultado.append({
            "id": p.id, "nombre": p.nombre, "descripcion": p.descripcion, "marca": p.marca,
            "genero": p.genero, "precio_venta": float(p.precio_venta), "imagen_url": url_imagen(p.imagen_url),
            **_precio_con_promocion(p, vigentes.get(p.id)),
            "categoria_id": p.categoria_id, "coleccion_id": p.coleccion_id,
            "publicado": bool(p.publicado),
            "disponible_total": disponible,
            "variantes": lista,
        })
    return resultado
