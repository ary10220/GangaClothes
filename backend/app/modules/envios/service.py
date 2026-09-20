"""Envios a domicilio de las compras en linea (CU29).

Reglas del modulo, todas en un lugar:

* El envio es de UNA venta y la venta tiene a lo sumo UN envio. Existe solo si
  el cliente eligio "delivery"; con "retiro en sucursal" no hay fila.
* El costo lo calcula siempre `tarifa.py` en el servidor. La pantalla lo
  muestra, no lo propone: si el precio viniera del navegador, cualquiera
  pediria envio gratis.
* El envio se arma ANTES de pagar (con la venta en carrito o pendiente) y su
  costo entra en `venta.total`, que es lo que la pasarela cobra. Mientras la
  compra no este pagada se recotiza sola: si el carrito cambia y cruza el
  minimo de envio gratis, el cliente lo ve enseguida.
* Un carrito vacio no paga envio: mientras no haya prendas, el costo es 0 aunque
  la direccion siga elegida.
* La cobertura se valida al elegir la direccion (`POST /api/envios`), que es
  donde el mensaje sirve. Despues, si el cliente cambia la sucursal de despacho
  por una que no llega hasta ahi, la compra vuelve sola a retiro en sucursal en
  vez de trabarle el carrito.
* El inventario NO lo toca este modulo. Se descuenta al pagarse, en `pagos`,
  como cualquier otra venta: entregar es mover un paquete que ya se cobro.
* Un envio aparece en el panel de la sucursal y en "mis envios" recien cuando
  la venta esta PAGADA. Un delivery a medio armar en un carrito todavia no es
  un pedido de nadie.

Los estados y quien los mueve:

    pendiente --asignar--> asignado --en_camino--> en_camino --entregar--> entregado
        |                     |                        |
        +---------------------+------------------------+--> cancelado

    El cliente solo puede deshacer su envio antes de pagar (vuelve a retiro en
    sucursal). Una vez cobrada la compra, el estado lo mueve el encargado.
"""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.fechas import utc_iso
from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.envios import Envio
from app.models.sucursales import Ciudad, Sucursal
from app.models.usuarios import Cliente, Usuario
from app.models.ventas import DetalleVenta, Pago, Venta
from app.modules.envios import tarifa
from app.modules.ventas import service as ventas

# Estados por los que pasa un envio y a cual puede ir cada uno.
ESTADOS = ("pendiente", "asignado", "en_camino", "entregado", "cancelado")
ACTIVOS = ("pendiente", "asignado", "en_camino")
SIGUIENTE = {"pendiente": "asignado", "asignado": "en_camino", "en_camino": "entregado"}

ETIQUETAS = {
    "pendiente": "Pendiente de asignar",
    "asignado": "Repartidor asignado",
    "en_camino": "En camino",
    "entregado": "Entregado",
    "cancelado": "Cancelado",
}

TIPOS_ENTREGA = ("sucursal", "delivery")


def _ahora() -> datetime:
    """Instante actual en UTC y sin zona, como lo guarda el resto del sistema."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


# ============================================================ lectura y salida
def _sucursal_despacho(db: Session, sucursal_id: int) -> Sucursal:
    """La sucursal desde la que sale el reparto; sin coordenadas no puede repartir."""
    sucursal = db.get(Sucursal, sucursal_id)
    if sucursal is None:
        raise HTTPException(404, "La sucursal no existe")
    if sucursal.latitud is None or sucursal.longitud is None:
        raise HTTPException(
            400,
            f"{sucursal.nombre} todavia no tiene su ubicacion en el mapa: un administrador "
            f"tiene que cargarle latitud y longitud para poder repartir desde ahi",
        )
    return sucursal


def _datos_sucursal(db: Session, sucursal: Sucursal | None) -> dict | None:
    if sucursal is None:
        return None
    ciudad = db.get(Ciudad, sucursal.ciudad_id)
    return {
        "id": sucursal.id,
        "nombre": sucursal.nombre,
        "direccion": sucursal.direccion,
        "telefono": sucursal.telefono,
        "ciudad": ciudad.nombre if ciudad else None,
        "latitud": sucursal.latitud,
        "longitud": sucursal.longitud,
    }


def _prendas(db: Session, venta_id: int) -> list[dict]:
    """Que lleva el paquete: lo justo para que el repartidor y el encargado lo armen."""
    filas = (
        db.query(DetalleVenta, Variante, Prenda, Talla, Color)
        .join(Variante, Variante.id == DetalleVenta.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(DetalleVenta.venta_id == venta_id)
        .order_by(DetalleVenta.id)
        .all()
    )
    return [{"id": d.id, "sku": v.sku, "prenda": p.nombre, "talla": t.nombre,
             "color": c.nombre, "cantidad": d.cantidad} for d, v, p, t, c in filas]


def _pago_de(db: Session, venta_id: int) -> dict | None:
    """El cobro exitoso de la compra, con su nombre legible ("Tarjeta (Stripe)")."""
    pago = (
        db.query(Pago)
        .filter(Pago.venta_id == venta_id, Pago.estado == "exitoso")
        .order_by(Pago.id.desc())
        .first()
    )
    if pago is None:
        return None
    return {
        "metodo": pago.metodo,
        "pasarela": pago.pasarela,
        "etiqueta": ventas.etiqueta_metodo(pago.metodo, pago.pasarela),
        "monto": float(ventas.dinero(pago.monto)),
        "referencia_externa": pago.referencia_externa,
        "fecha": utc_iso(pago.fecha),
    }


def salida(db: Session, envio: Envio, con_prendas: bool = True) -> dict:
    """La forma en que un envio sale por la API: la misma para la web y para Flutter."""
    venta = db.get(Venta, envio.venta_id)
    sucursal = db.get(Sucursal, venta.sucursal_id) if venta else None

    cliente = None
    if venta and venta.cliente_id:
        cl = db.get(Cliente, venta.cliente_id)
        u = db.get(Usuario, cl.usuario_id) if cl else None
        cliente = {
            "id": venta.cliente_id,
            "nombre": " ".join(filter(None, [u.nombre, u.apellido])) if u else None,
            "email": u.email if u else None,
            "telefono": u.telefono if u else None,
        }

    return {
        "id": envio.id,
        "estado": envio.estado,
        "etiqueta_estado": ETIQUETAS.get(envio.estado, envio.estado),
        "activo": envio.estado in ACTIVOS,
        "direccion": envio.direccion,
        "latitud": envio.latitud,
        "longitud": envio.longitud,
        "referencia": envio.referencia,
        "telefono_contacto": envio.telefono_contacto,
        "distancia_km": float(Decimal(str(envio.distancia_km or 0))),
        "costo_envio": float(ventas.dinero(envio.costo_envio)),
        "express": bool(envio.express),
        "repartidor": envio.repartidor,
        "motivo_cancelacion": envio.motivo_cancelacion,
        "fecha_creacion": utc_iso(envio.fecha_creacion),
        "fecha_asignacion": utc_iso(envio.fecha_asignacion),
        "fecha_salida": utc_iso(envio.fecha_salida),
        "fecha_estimada": utc_iso(envio.fecha_estimada),
        "fecha_entrega": utc_iso(envio.fecha_entrega),
        # De donde sale: la sucursal que despacha la venta, con su punto en el mapa.
        "sucursal": _datos_sucursal(db, sucursal),
        "cliente": cliente,
        "venta": {
            "id": venta.id,
            "estado": venta.estado,
            "canal": venta.canal,
            "fecha": utc_iso(venta.fecha),
            "nro_comprobante": venta.nro_comprobante,
            "subtotal": float(ventas.dinero(venta.subtotal)),
            "descuento": float(ventas.dinero(venta.descuento)),
            "costo_envio": float(ventas.dinero(venta.costo_envio)),
            "total": float(ventas.dinero(venta.total)),
        } if venta else None,
        # Con que se pago la compra que se esta repartiendo: el cliente lo
        # quiere ver en su seguimiento y el encargado, al despachar, tiene que
        # saber que el paquete ya esta cobrado y no hay que cobrar en la puerta.
        "pago": _pago_de(db, envio.venta_id),
        "prendas": _prendas(db, envio.venta_id) if con_prendas else [],
    }


def de_venta(db: Session, venta_id: int) -> Envio | None:
    return db.query(Envio).filter(Envio.venta_id == venta_id).first()


# ================================================================== cotizacion
def _carrito_del_cliente(db: Session, usuario: Usuario) -> Venta | None:
    """El carrito o la compra recien confirmada del cliente, para tomar de ahi
    la sucursal y el monto por defecto de la cotizacion."""
    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
    if cliente is None:
        return None
    return (
        db.query(Venta)
        .filter(Venta.cliente_id == cliente.id, Venta.estado.in_(["carrito", "pendiente"]),
                Venta.canal.in_(["web", "movil"]))
        .order_by(Venta.id.desc())
        .first()
    )


def cotizar(db: Session, usuario: Usuario, datos) -> dict:
    """Distancia, costo desglosado y tiempo estimado. NO crea ni cambia nada.

    Sin `sucursal_id` ni `monto_compra` se usan los del carrito del cliente,
    que es como la llama el checkout; mandandolos se puede cotizar cualquier
    punto (lo aprovechan las pruebas y la app movil).
    """
    tarifa.validar_coordenadas(datos.latitud, datos.longitud)

    venta = _carrito_del_cliente(db, usuario)
    sucursal_id = datos.sucursal_id or (venta.sucursal_id if venta else None)
    if sucursal_id is None:
        raise HTTPException(400, "Indica desde que sucursal se despacha (sucursal_id)")
    sucursal = _sucursal_despacho(db, sucursal_id)

    if datos.monto_compra is not None:
        monto = ventas.dinero(datos.monto_compra)
    elif venta is not None:
        # El total del carrito SIN el envio: el envio gratis se decide por lo
        # que vale la mercaderia, no por lo que ya se le sumo de reparto.
        monto = ventas.dinero(venta.subtotal) - ventas.dinero(venta.descuento)
    else:
        monto = Decimal("0")

    distancia = tarifa.distancia_km(sucursal.latitud, sucursal.longitud,
                                    datos.latitud, datos.longitud)
    cotizacion = tarifa.cotizar(distancia, monto, datos.express)
    minutos = cotizacion["minutos_estimados"]
    return {
        **cotizacion,
        "sucursal": _datos_sucursal(db, sucursal),
        "destino": {"latitud": datos.latitud, "longitud": datos.longitud},
        "monto_compra": float(monto),
        "total_a_pagar": float(monto + ventas.dinero(cotizacion["costo_envio"])),
        "entrega_estimada": utc_iso(tarifa.fecha_estimada(minutos)),
        "mensaje_cobertura": None if cotizacion["dentro_de_cobertura"] else (
            f"Tu direccion esta a {cotizacion['distancia_km']} km de {sucursal.nombre} y "
            f"repartimos hasta {cotizacion['cobertura_km']:.0f} km. Elegi retiro en sucursal "
            f"o cambia la sucursal de despacho"
        ),
        "tarifa": tarifa.parametros(),
    }


# ============================================= el envio dentro de una compra
def recotizar(db: Session, venta: Venta, monto_mercaderia: Decimal, hay_prendas: bool = True) -> Decimal:
    """Recalcula el envio de una venta que todavia no se pago y devuelve su costo.

    La llama `ventas.recalcular` en cada cambio del carrito, y rehace las dos
    mitades del calculo, porque las dos pueden haber cambiado:

      * la DISTANCIA, si el cliente cambio la sucursal desde la que se despacha;
      * el COSTO, si el carrito cruzo (o dejo de cruzar) el minimo de envio gratis.

    Nunca falla: es la cola de operaciones del carrito (agregar, quitar, cambiar
    de sucursal) y ninguna de esas deberia romperse por el envio. Si con la
    sucursal nueva el destino queda fuera de cobertura, o esa sucursal no tiene
    punto en el mapa, la compra vuelve a RETIRO EN SUCURSAL y el envio se
    descarta: es mejor que el cliente vea que la entrega se deshizo, y pueda
    elegir otra direccion, a que pague un reparto que nadie puede hacer.

    Un envio que ya no esta pendiente no se recotiza: una vez asignado, el
    precio es el que el cliente pago.
    """
    envio = de_venta(db, venta.id)
    if envio is None:
        # "delivery" sin envio no existe: la venta vuelve a ser retiro en sucursal.
        venta.tipo_entrega = "sucursal"
        return Decimal("0")
    if envio.estado != "pendiente":
        return ventas.dinero(envio.costo_envio)
    if not hay_prendas:
        # Un carrito vacio no paga envio: no hay nada que llevar. La direccion
        # queda guardada por si el cliente vuelve a cargar prendas.
        envio.costo_envio = Decimal("0")
        return Decimal("0")

    sucursal = db.get(Sucursal, venta.sucursal_id)
    if sucursal is None or sucursal.latitud is None or sucursal.longitud is None:
        return _deshacer(db, venta, envio)

    distancia = tarifa.distancia_km(sucursal.latitud, sucursal.longitud,
                                    envio.latitud, envio.longitud)
    cotizacion = tarifa.cotizar(distancia, monto_mercaderia, bool(envio.express))
    if not cotizacion["dentro_de_cobertura"]:
        return _deshacer(db, venta, envio)

    envio.distancia_km = Decimal(str(cotizacion["distancia_km"]))
    envio.costo_envio = ventas.dinero(cotizacion["costo_envio"])
    envio.fecha_estimada = tarifa.fecha_estimada(cotizacion["minutos_estimados"])
    return ventas.dinero(envio.costo_envio)


def _deshacer(db: Session, venta: Venta, envio: Envio) -> Decimal:
    """Descarta un envio que ya no se puede hacer y vuelve a retiro en sucursal."""
    db.delete(envio)
    venta.tipo_entrega = "sucursal"
    return Decimal("0")


def _venta_del_cliente(db: Session, usuario: Usuario, venta_id: int) -> Venta:
    cliente = ventas.cliente_de(db, usuario, "pedir un envio a domicilio")
    venta = db.get(Venta, venta_id)
    if venta is None:
        raise HTTPException(404, "La compra no existe")
    if venta.cliente_id != cliente.id:
        raise HTTPException(403, "Solo puedes pedir el envio de tus propias compras")
    return venta


def crear(db: Session, usuario: Usuario, datos) -> dict:
    """Pone (o cambia) la entrega a domicilio de una compra que todavia no se pago.

    Es idempotente a proposito: si la pasarela rechaza el pago, la venta vuelve
    al carrito y el cliente reintenta; esta misma llamada actualiza el envio que
    ya existia con una cotizacion fresca en lugar de fallar por duplicado.
    """
    tarifa.validar_coordenadas(datos.latitud, datos.longitud)
    venta = _venta_del_cliente(db, usuario, datos.venta_id)

    if venta.canal == "caja":
        raise HTTPException(400, "Una venta de caja se entrega en el mostrador")
    if venta.estado not in ("carrito", "pendiente"):
        raise HTTPException(
            400,
            f"La compra #{venta.id} esta '{venta.estado}': la entrega se elige antes de pagar"
        )
    if not db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta.id).first():
        raise HTTPException(400, "El carrito esta vacio: agrega prendas antes de pedir el envio")

    sucursal = _sucursal_despacho(db, venta.sucursal_id)
    distancia = tarifa.distancia_km(sucursal.latitud, sucursal.longitud,
                                    datos.latitud, datos.longitud)
    monto = ventas.dinero(venta.subtotal) - ventas.dinero(venta.descuento)
    cotizacion = tarifa.cotizar(distancia, monto, datos.express)
    if not cotizacion["dentro_de_cobertura"]:
        raise HTTPException(
            400,
            f"No repartimos hasta ahi: son {cotizacion['distancia_km']} km desde {sucursal.nombre} "
            f"y la cobertura llega a {cotizacion['cobertura_km']:.0f} km"
        )

    envio = de_venta(db, venta.id)
    if envio is not None and envio.estado != "pendiente":
        raise HTTPException(400, f"El envio #{envio.id} ya esta '{envio.estado}': no se puede cambiar")
    if envio is None:
        envio = Envio(venta_id=venta.id)
        db.add(envio)

    envio.direccion = datos.direccion.strip()
    envio.latitud, envio.longitud = datos.latitud, datos.longitud
    envio.referencia = (datos.referencia or "").strip() or None
    envio.telefono_contacto = datos.telefono_contacto.strip()
    envio.express = bool(datos.express)
    envio.estado = "pendiente"
    envio.distancia_km = Decimal(str(cotizacion["distancia_km"]))
    envio.costo_envio = ventas.dinero(cotizacion["costo_envio"])
    envio.fecha_estimada = tarifa.fecha_estimada(cotizacion["minutos_estimados"])

    venta.tipo_entrega = "delivery"
    # recalcular() vuelve a pedirle el costo a recotizar() y lo suma al total.
    ventas.recalcular(db, venta)
    db.commit()

    return {
        "envio": salida(db, db.get(Envio, envio.id)),
        "cotizacion": cotizacion,
        "venta": ventas.salida(db, db.get(Venta, venta.id), con_stock=venta.estado == "carrito"),
    }


def quitar(db: Session, usuario: Usuario, envio_id: int) -> dict:
    """El cliente se arrepiente y vuelve a retiro en sucursal, antes de pagar."""
    envio = db.get(Envio, envio_id)
    if envio is None:
        raise HTTPException(404, "El envio no existe")
    venta = _venta_del_cliente(db, usuario, envio.venta_id)
    if venta.estado not in ("carrito", "pendiente") or envio.estado != "pendiente":
        raise HTTPException(400, "Esta compra ya se pago: el envio lo cancela la tienda")

    db.delete(envio)
    venta.tipo_entrega = "sucursal"
    venta.costo_envio = Decimal("0")
    ventas.recalcular(db, venta)
    db.commit()
    return ventas.salida(db, db.get(Venta, venta.id), con_stock=venta.estado == "carrito")


# ==================================================================== consultas
def _pagadas(consulta):
    """Un envio es un pedido de verdad recien cuando la compra esta pagada."""
    return consulta.join(Venta, Venta.id == Envio.venta_id).filter(Venta.estado == "pagada")


def mios(db: Session, usuario: Usuario) -> list[dict]:
    """Los envios del cliente autenticado, del mas nuevo al mas viejo."""
    cliente = ventas.cliente_de(db, usuario, "consultar sus envios")
    filas = (
        _pagadas(db.query(Envio))
        .filter(Venta.cliente_id == cliente.id)
        .order_by(Envio.id.desc())
        .all()
    )
    return [salida(db, e) for e in filas]


def listar(db: Session, sucursal_id: int | None = None, estado: str | None = None) -> list[dict]:
    """Envios de una sucursal para el encargado. Los activos primero y, dentro
    de cada grupo, el mas viejo arriba: ese es el que hay que despachar ya."""
    if estado is not None and estado not in ESTADOS:
        raise HTTPException(400, f"Estado invalido. Use uno de: {', '.join(ESTADOS)}")
    consulta = _pagadas(db.query(Envio))
    if sucursal_id is not None:
        consulta = consulta.filter(Venta.sucursal_id == sucursal_id)
    if estado is not None:
        consulta = consulta.filter(Envio.estado == estado)
    filas = consulta.order_by(Envio.id.desc()).all()
    orden = {e: i for i, e in enumerate(ESTADOS)}
    filas.sort(key=lambda e: (orden.get(e.estado, 99), e.id))
    return [salida(db, e) for e in filas]


def ver(db: Session, usuario: Usuario, envio_id: int, personal: bool) -> dict:
    """Un envio: el personal ve cualquiera; un cliente, solo los suyos."""
    envio = db.get(Envio, envio_id)
    if envio is None:
        raise HTTPException(404, "El envio no existe")
    if not personal:
        cliente = ventas.cliente_de(db, usuario, "consultar sus envios")
        venta = db.get(Venta, envio.venta_id)
        if venta is None or venta.cliente_id != cliente.id:
            raise HTTPException(403, "Solo puedes seguir tus propios envios")
    return salida(db, envio)


# ================================================================ transiciones
def _para_mover(db: Session, envio_id: int, desde: tuple[str, ...], accion: str) -> Envio:
    envio = db.get(Envio, envio_id)
    if envio is None:
        raise HTTPException(404, "El envio no existe")
    venta = db.get(Venta, envio.venta_id)
    if venta is None or venta.estado != "pagada":
        raise HTTPException(400, "La compra todavia no esta pagada: no hay nada que despachar")
    if envio.estado not in desde:
        esperado = " o ".join(f"'{e}'" for e in desde)
        raise HTTPException(
            400,
            f"El envio #{envio.id} esta '{envio.estado}' y para {accion} tiene que estar {esperado}"
        )
    return envio


def asignar(db: Session, envio_id: int, repartidor: str) -> dict:
    """pendiente -> asignado. El repartidor es simulado: se escribe su nombre."""
    envio = _para_mover(db, envio_id, ("pendiente",), "asignar repartidor")
    envio.estado = "asignado"
    envio.repartidor = repartidor.strip()
    envio.fecha_asignacion = _ahora()
    # La estimacion se vuelve a contar desde que sale el pedido de verdad.
    envio.fecha_estimada = tarifa.fecha_estimada(
        tarifa.minutos_estimados(envio.distancia_km, bool(envio.express)), envio.fecha_asignacion
    )
    db.commit()
    return salida(db, db.get(Envio, envio_id))


def en_camino(db: Session, envio_id: int) -> dict:
    """asignado -> en_camino: el repartidor salio con el paquete."""
    envio = _para_mover(db, envio_id, ("asignado",), "marcarlo en camino")
    envio.estado = "en_camino"
    envio.fecha_salida = _ahora()
    db.commit()
    return salida(db, db.get(Envio, envio_id))


def entregar(db: Session, envio_id: int) -> dict:
    """en_camino -> entregado: el cliente ya lo tiene."""
    envio = _para_mover(db, envio_id, ("en_camino",), "marcarlo entregado")
    envio.estado = "entregado"
    envio.fecha_entrega = _ahora()
    db.commit()
    return salida(db, db.get(Envio, envio_id))


def cancelar(db: Session, envio_id: int, motivo: str | None = None) -> dict:
    """El pedido no se entrega a domicilio (nadie atendio, direccion equivocada...).

    Cancelar el ENVIO no anula la VENTA: la compra ya se cobro y el inventario ya
    salio. Lo que queda es coordinar con el cliente el retiro en sucursal o una
    devolucion, que es el CU de anulacion de ventas y no entra en este ciclo.
    """
    envio = _para_mover(db, envio_id, ACTIVOS, "cancelarlo")
    envio.estado = "cancelado"
    envio.motivo_cancelacion = (motivo or "").strip() or None
    db.commit()
    return salida(db, db.get(Envio, envio_id))
