"""Promociones (CU18): descuentos por prenda con fechas de vigencia.

Este modulo es la unica fuente del precio con descuento. El catalogo publico,
el carrito y la caja le preguntan a `vigentes_por_prenda` y a `aplicar`; nadie
mas calcula descuentos por su cuenta.

Reglas:
- Una promocion rige si esta activa y hoy cae entre fecha_inicio y fecha_fin
  (ambas inclusive, hora de Bolivia).
- Los descuentos NO se acumulan. Si dos promociones vigentes alcanzan a la misma
  prenda, se aplica la que mas le rebaja al cliente, y el panel lo advierte
  como solapamiento para que el administrador lo corrija.
- Un descuento por monto nunca puede dejar una prenda en cero o negativo.
"""
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException

from app.core import fechas
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.catalogo import Prenda
from app.models.ventas import DetalleVenta, Promocion, PromocionPrenda

CENTAVO = Decimal("0.01")
TIPOS = {"porcentaje", "monto"}
# Tope de un descuento porcentual: mas que esto casi seguro es un error de tipeo.
PORCENTAJE_MAXIMO = Decimal("90")


def hoy_bolivia() -> date:
    """El dia de hoy en Bolivia. La zona se define en un solo lugar: core/fechas.py."""
    return fechas.hoy_bolivia()


def _dinero(valor) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVO)


# ------------------------------------------------------- calculo del descuento
def descuento_unitario(precio, tipo: str, valor) -> Decimal:
    """Cuanto se le rebaja a UNA unidad de ese precio."""
    precio = _dinero(precio)
    if tipo == "porcentaje":
        # Medio centavo se redondea hacia arriba, como lo hace cualquier caja.
        rebaja = (precio * Decimal(str(valor)) / Decimal("100")).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    else:
        rebaja = _dinero(valor)
    # Nunca se regala la prenda ni se paga por llevarsela.
    return max(min(rebaja, precio - CENTAVO), Decimal("0"))


def estado_de(promo: Promocion, hoy: date | None = None) -> str:
    hoy = hoy or hoy_bolivia()
    if promo.activo is False:
        return "inactiva"
    if promo.fecha_inicio and hoy < promo.fecha_inicio:
        return "programada"
    if promo.fecha_fin and hoy > promo.fecha_fin:
        return "vencida"
    return "vigente"


def vigentes_por_prenda(db: Session, prenda_ids: list[int] | None = None,
                        hoy: date | None = None) -> dict[int, list[Promocion]]:
    """prenda_id -> promociones vigentes hoy que la alcanzan."""
    hoy = hoy or hoy_bolivia()
    consulta = (
        db.query(PromocionPrenda.prenda_id, Promocion)
        .join(Promocion, Promocion.id == PromocionPrenda.promocion_id)
        .filter(Promocion.activo.isnot(False),
                Promocion.fecha_inicio <= hoy, Promocion.fecha_fin >= hoy)
    )
    if prenda_ids is not None:
        if not prenda_ids:
            return {}
        consulta = consulta.filter(PromocionPrenda.prenda_id.in_(prenda_ids))
    salida: dict[int, list[Promocion]] = {}
    for prenda_id, promo in consulta.order_by(Promocion.id).all():
        salida.setdefault(prenda_id, []).append(promo)
    return salida


def aplicar(precio, promociones: list[Promocion] | None) -> dict:
    """Precio final de una unidad. De varias promociones gana la de mayor rebaja."""
    precio = _dinero(precio)
    mejor, rebaja = None, Decimal("0")
    for promo in promociones or []:
        r = descuento_unitario(precio, promo.tipo_descuento, promo.valor)
        if r > rebaja:
            mejor, rebaja = promo, r
    return {
        "precio_lista": precio,
        "descuento": rebaja,
        "precio_final": precio - rebaja,
        "promocion": mejor,
    }


def etiqueta(promo: Promocion) -> str:
    valor = float(promo.valor)
    return f"-{valor:g}%" if promo.tipo_descuento == "porcentaje" else f"-Bs {valor:g}"


def resumen_publico(promo: Promocion | None) -> dict | None:
    """Lo que ve el cliente de la promocion aplicada."""
    if promo is None:
        return None
    return {
        "id": promo.id,
        "nombre": promo.nombre,
        "tipo_descuento": promo.tipo_descuento,
        "valor": float(promo.valor),
        "etiqueta": etiqueta(promo),
        "fecha_fin": promo.fecha_fin.isoformat() if promo.fecha_fin else None,
    }


# ------------------------------------------------------------ solapamientos
def _se_cruzan(a: Promocion, b: Promocion) -> bool:
    return a.fecha_inicio <= b.fecha_fin and b.fecha_inicio <= a.fecha_fin


def solapamientos(db: Session, promo: Promocion) -> list[dict]:
    """Otras promociones activas que comparten prendas y fechas con esta."""
    if promo.activo is False:
        return []
    mis_prendas = [f[0] for f in db.query(PromocionPrenda.prenda_id)
                   .filter(PromocionPrenda.promocion_id == promo.id).all()]
    if not mis_prendas:
        return []
    filas = (
        db.query(Promocion, Prenda)
        .join(PromocionPrenda, PromocionPrenda.promocion_id == Promocion.id)
        .join(Prenda, Prenda.id == PromocionPrenda.prenda_id)
        .filter(Promocion.id != promo.id, Promocion.activo.isnot(False),
                PromocionPrenda.prenda_id.in_(mis_prendas))
        .order_by(Promocion.id, Prenda.nombre)
        .all()
    )
    por_promo: dict[int, dict] = {}
    for otra, prenda in filas:
        if not _se_cruzan(promo, otra):
            continue
        item = por_promo.setdefault(otra.id, {
            "promocion_id": otra.id,
            "promocion": otra.nombre,
            "desde": max(promo.fecha_inicio, otra.fecha_inicio).isoformat(),
            "hasta": min(promo.fecha_fin, otra.fecha_fin).isoformat(),
            "prendas": [],
        })
        item["prendas"].append(prenda.nombre)
    return list(por_promo.values())


def texto_solapamientos(cruces: list[dict]) -> str | None:
    if not cruces:
        return None
    partes = [f"'{c['promocion']}' ({', '.join(c['prendas'])}; del {c['desde']} al {c['hasta']})"
              for c in cruces]
    return ("Se solapa con " + "; ".join(partes) +
            ". Los descuentos no se acumulan: en esas prendas se aplica el mayor de los dos")


# ------------------------------------------------------------------- salida
def salida(db: Session, promo: Promocion, hoy: date | None = None) -> dict:
    prendas = (
        db.query(Prenda)
        .join(PromocionPrenda, PromocionPrenda.prenda_id == Prenda.id)
        .filter(PromocionPrenda.promocion_id == promo.id)
        .order_by(Prenda.nombre)
        .all()
    )
    cruces = solapamientos(db, promo)
    lista = []
    for p in prendas:
        rebaja = descuento_unitario(p.precio_venta, promo.tipo_descuento, promo.valor)
        lista.append({
            "id": p.id, "nombre": p.nombre, "imagen_url": p.imagen_url,
            "precio_venta": float(p.precio_venta),
            "precio_final": float(_dinero(p.precio_venta) - rebaja),
            "costo": float(p.costo),
            # Vender por debajo del costo es una decision valida, pero hay que verla.
            "bajo_costo": _dinero(p.precio_venta) - rebaja < _dinero(p.costo),
        })
    return {
        "id": promo.id,
        "nombre": promo.nombre,
        "descripcion": promo.descripcion,
        "tipo_descuento": promo.tipo_descuento,
        "valor": float(promo.valor),
        "etiqueta": etiqueta(promo),
        "fecha_inicio": promo.fecha_inicio.isoformat() if promo.fecha_inicio else None,
        "fecha_fin": promo.fecha_fin.isoformat() if promo.fecha_fin else None,
        "activo": promo.activo is not False,
        "estado": estado_de(promo, hoy),
        "prenda_ids": [p.id for p in prendas],
        "prendas": lista,
        "solapamientos": cruces,
        "advertencia": texto_solapamientos(cruces),
    }


def listar(db: Session) -> list[dict]:
    hoy = hoy_bolivia()
    promos = db.query(Promocion).order_by(Promocion.fecha_inicio.desc(), Promocion.id.desc()).all()
    return [salida(db, p, hoy) for p in promos]


def _existe(db: Session, promo_id: int) -> Promocion:
    promo = db.get(Promocion, promo_id)
    if promo is None:
        raise HTTPException(404, "Promocion no encontrada")
    return promo


def obtener(db: Session, promo_id: int) -> dict:
    return salida(db, _existe(db, promo_id))


# --------------------------------------------------------------- escritura
def _validar(db: Session, promo: Promocion, prenda_ids: list[int]) -> list[int]:
    promo.nombre = (promo.nombre or "").strip()
    if not promo.nombre:
        raise HTTPException(400, "El nombre es obligatorio")
    if promo.tipo_descuento not in TIPOS:
        raise HTTPException(400, "El tipo de descuento es 'porcentaje' o 'monto'")
    if promo.fecha_inicio is None or promo.fecha_fin is None:
        raise HTTPException(400, "La promocion necesita fecha de inicio y de fin")
    if promo.fecha_fin < promo.fecha_inicio:
        raise HTTPException(400, "La fecha de fin no puede ser anterior a la de inicio")
    valor = Decimal(str(promo.valor))
    if valor <= 0:
        raise HTTPException(400, "El valor del descuento debe ser mayor que cero")
    if promo.tipo_descuento == "porcentaje" and valor > PORCENTAJE_MAXIMO:
        raise HTTPException(400, f"Un descuento porcentual va de 1 a {PORCENTAJE_MAXIMO:g}")

    ids = list(dict.fromkeys(prenda_ids))
    if ids:
        prendas = {p.id: p for p in db.query(Prenda).filter(Prenda.id.in_(ids)).all()}
        faltan = [i for i in ids if i not in prendas]
        if faltan:
            raise HTTPException(400, f"Prendas inexistentes: {faltan}")
        if promo.tipo_descuento == "monto":
            caras = [f"{p.nombre} (Bs {float(p.precio_venta):.2f})" for p in prendas.values()
                     if _dinero(p.precio_venta) <= _dinero(valor)]
            if caras:
                raise HTTPException(
                    400, f"Un descuento de Bs {float(valor):.2f} iguala o supera el precio de: "
                         f"{', '.join(caras)}. Baja el monto o quita esas prendas")
    return ids


def _asociar(db: Session, promo: Promocion, ids: list[int]) -> None:
    actuales = {pp.prenda_id: pp for pp in db.query(PromocionPrenda)
                .filter(PromocionPrenda.promocion_id == promo.id).all()}
    for prenda_id, fila in actuales.items():
        if prenda_id not in ids:
            db.delete(fila)
    for prenda_id in ids:
        if prenda_id not in actuales:
            db.add(PromocionPrenda(promocion_id=promo.id, prenda_id=prenda_id))


def crear(db: Session, datos) -> dict:
    campos = datos.model_dump(exclude={"prenda_ids"})
    promo = Promocion(**campos)
    ids = _validar(db, promo, datos.prenda_ids)
    db.add(promo)
    db.flush()
    _asociar(db, promo, ids)
    db.commit()
    return salida(db, db.get(Promocion, promo.id))


def editar(db: Session, promo_id: int, datos) -> dict:
    promo = _existe(db, promo_id)
    cambios = datos.model_dump(exclude_unset=True)
    prenda_ids = cambios.pop("prenda_ids", None)
    for clave, valor in cambios.items():
        if valor is None and clave != "descripcion":
            continue
        setattr(promo, clave, valor)
    if prenda_ids is None:
        prenda_ids = [f[0] for f in db.query(PromocionPrenda.prenda_id)
                      .filter(PromocionPrenda.promocion_id == promo.id).all()]
    ids = _validar(db, promo, prenda_ids)
    _asociar(db, promo, ids)
    db.commit()
    return salida(db, db.get(Promocion, promo.id))


def eliminar(db: Session, promo_id: int) -> tuple[str, bool]:
    """Devuelve (nombre, eliminada). Una promocion que ya dio descuentos en alguna
    venta no se borra: se desactiva, para no perder el rastro en los comprobantes."""
    promo = _existe(db, promo_id)
    nombre = promo.nombre
    usada = db.query(DetalleVenta.id).filter(DetalleVenta.promocion_id == promo.id).first()
    if usada:
        promo.activo = False
        db.commit()
        return nombre, False
    try:
        db.query(PromocionPrenda).filter(PromocionPrenda.promocion_id == promo.id).delete()
        db.delete(promo)
        db.commit()
    except IntegrityError:
        db.rollback()
        promo = _existe(db, promo_id)
        promo.activo = False
        db.commit()
        return nombre, False
    return nombre, True
