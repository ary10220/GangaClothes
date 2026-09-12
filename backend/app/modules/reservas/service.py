"""Reglas de reservas: apartar stock para probarse la ropa en tienda.

Reservar no descuenta `cantidad`: suma `cantidad_reservada`, que es lo que
separa las unidades del disponible (cantidad - reservada) hasta que la reserva
termina. La venta real (modulo ventas) es la que descuenta la cantidad.

Concurrencia: el stock se aparta con un UPDATE condicional
(`WHERE cantidad - cantidad_reservada >= n`) y los cambios de estado con
`WHERE estado IN (...)`. Asi, si dos clientes piden la ultima unidad a la vez,
o una reserva se cancela dos veces al mismo tiempo, la base garantiza que solo
una operacion gana, sin depender del orden en que llegan las peticiones.
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import case, update
from sqlalchemy.orm import Session

from app.models.catalogo import Color, Prenda, Talla, Variante
from app.models.inventario import Inventario
from app.models.sucursales import Sucursal
from app.models.usuarios import Cliente, Usuario
from app.models.ventas import DetalleReserva, Reserva

ESTADOS = {"pendiente", "preparada", "atendida", "cancelada", "expirada"}
# Mientras la reserva esta en alguno de estos estados, retiene stock.
ACTIVAS = {"pendiente", "preparada"}


# ------------------------------------------------------------ identidad
def cliente_de(db: Session, usuario: Usuario) -> Cliente:
    """El perfil de cliente del usuario del token, o 403 si no lo tiene."""
    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
    if cliente is None:
        raise HTTPException(403, "Solo los clientes pueden reservar y consultar sus reservas")
    return cliente


# ---------------------------------------------------------- presentacion
def _salida(db: Session, reserva: Reserva, con_cliente: bool = False) -> dict:
    sucursal = db.get(Sucursal, reserva.sucursal_id)
    filas = (
        db.query(DetalleReserva, Variante, Prenda, Talla, Color)
        .join(Variante, Variante.id == DetalleReserva.variante_id)
        .join(Prenda, Prenda.id == Variante.prenda_id)
        .join(Talla, Talla.id == Variante.talla_id)
        .join(Color, Color.id == Variante.color_id)
        .filter(DetalleReserva.reserva_id == reserva.id)
        .order_by(DetalleReserva.id)
        .all()
    )
    detalle = [{
        "id": d.id,
        "variante_id": d.variante_id,
        "sku": v.sku,
        "prenda": p.nombre,
        "talla": t.nombre,
        "color": c.nombre,
        "cantidad": d.cantidad,
        # "reservado" mientras retiene stock; "liberado" cuando ya lo devolvio.
        "estado": d.estado,
    } for d, v, p, t, c in filas]

    salida = {
        "id": reserva.id,
        "estado": reserva.estado,
        "fecha_creacion": reserva.fecha_creacion.isoformat() if reserva.fecha_creacion else None,
        "fecha_hora_prueba": reserva.fecha_hora_prueba.isoformat() if reserva.fecha_hora_prueba else None,
        "notas": reserva.notas,
        "sucursal_id": reserva.sucursal_id,
        "sucursal": sucursal.nombre if sucursal else None,
        "unidades": sum(d["cantidad"] for d in detalle),
        "detalle": detalle,
    }
    if con_cliente:
        cliente = db.get(Cliente, reserva.cliente_id)
        usuario = db.get(Usuario, cliente.usuario_id) if cliente else None
        salida["cliente"] = {
            "id": reserva.cliente_id,
            "nombre": " ".join(filter(None, [usuario.nombre, usuario.apellido])) if usuario else None,
            "email": usuario.email if usuario else None,
            "telefono": usuario.telefono if usuario else None,
        }
    return salida


# ----------------------------------------------------------------- CU23
def _hora_del_servidor(fecha: datetime) -> datetime:
    """La columna no guarda zona horaria: una fecha con zona se pasa a la hora local."""
    if fecha.tzinfo is not None:
        fecha = fecha.astimezone().replace(tzinfo=None)
    return fecha


def crear(db: Session, usuario: Usuario, datos) -> dict:
    cliente = cliente_de(db, usuario)

    sucursal = db.get(Sucursal, datos.sucursal_id)
    if sucursal is None:
        raise HTTPException(404, "La sucursal no existe")
    if sucursal.activo is False:
        raise HTTPException(400, f"La {sucursal.nombre} no esta recibiendo reservas")

    fecha = _hora_del_servidor(datos.fecha_hora_prueba)
    if fecha <= datetime.now():
        raise HTTPException(400, "La fecha y hora de prueba tiene que ser futura")

    if not datos.detalle:
        raise HTTPException(400, "La reserva necesita al menos una prenda")
    ids = [linea.variante_id for linea in datos.detalle]
    repetidas = sorted({i for i in ids if ids.count(i) > 1})
    if repetidas:
        raise HTTPException(400, f"Variantes repetidas en el detalle: {repetidas}. Junta las cantidades en una linea")

    # 1) Se revisan TODAS las lineas antes de tocar nada, para poder decir
    #    exactamente cuales fallan y no rechazar de a una por intento.
    faltantes, inventarios = [], {}
    for linea in datos.detalle:
        fila = (
            db.query(Variante, Prenda, Talla, Color)
            .join(Prenda, Prenda.id == Variante.prenda_id)
            .join(Talla, Talla.id == Variante.talla_id)
            .join(Color, Color.id == Variante.color_id)
            .filter(Variante.id == linea.variante_id)
            .first()
        )
        if fila is None:
            faltantes.append(f"la variante {linea.variante_id} no existe")
            continue
        variante, prenda, talla, color = fila
        nombre = f"{variante.sku} ({prenda.nombre}, {talla.nombre}/{color.nombre})"
        if variante.activo is False or prenda.activo is False:
            faltantes.append(f"{nombre}: ya no esta a la venta")
            continue

        inv = (
            db.query(Inventario)
            .filter(Inventario.variante_id == linea.variante_id,
                    Inventario.sucursal_id == datos.sucursal_id)
            .first()
        )
        disponible = (inv.cantidad - inv.cantidad_reservada) if inv else 0
        if linea.cantidad > disponible:
            faltantes.append(f"{nombre}: pediste {linea.cantidad} y hay {disponible} disponibles")
            continue
        inventarios[linea.variante_id] = (inv.id, nombre)

    if faltantes:
        raise HTTPException(
            400, f"No se pudo reservar en {sucursal.nombre}. " + "; ".join(faltantes)
        )

    # 2) Todo o nada: reserva, detalle y stock apartado van en una transaccion.
    reserva = Reserva(cliente_id=cliente.id, sucursal_id=datos.sucursal_id,
                      fecha_hora_prueba=fecha, estado="pendiente", notas=datos.notas)
    db.add(reserva)
    db.flush()

    for linea in datos.detalle:
        inv_id, nombre = inventarios[linea.variante_id]
        resultado = db.execute(
            update(Inventario)
            .where(Inventario.id == inv_id,
                   Inventario.cantidad - Inventario.cantidad_reservada >= linea.cantidad)
            .values(cantidad_reservada=Inventario.cantidad_reservada + linea.cantidad)
            .execution_options(synchronize_session=False)
        )
        if resultado.rowcount != 1:
            # Alguien aparto esas unidades entre la revision y este UPDATE.
            db.rollback()
            raise HTTPException(
                400, f"No se pudo reservar: {nombre} se acaba de agotar. Intenta de nuevo"
            )
        db.add(DetalleReserva(reserva_id=reserva.id, variante_id=linea.variante_id,
                              cantidad=linea.cantidad, estado="reservado"))

    db.commit()
    return _salida(db, db.get(Reserva, reserva.id))


# ----------------------------------------------------------------- CU24
def mias(db: Session, usuario: Usuario) -> list[dict]:
    cliente = cliente_de(db, usuario)
    filas = (
        db.query(Reserva)
        .filter(Reserva.cliente_id == cliente.id)
        .order_by(Reserva.fecha_creacion.desc(), Reserva.id.desc())
        .all()
    )
    return [_salida(db, r) for r in filas]


def cancelar(db: Session, usuario: Usuario, reserva_id: int) -> tuple[dict, int]:
    cliente = cliente_de(db, usuario)
    reserva = db.get(Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(404, "Reserva no encontrada")
    # El dueno se revisa antes que el estado: no se revela nada de reservas ajenas.
    if reserva.cliente_id != cliente.id:
        raise HTTPException(403, "Solo puedes cancelar tus propias reservas")
    liberadas = _cambiar_estado(db, reserva_id, ACTIVAS, "cancelada", liberar=True, verbo="cancelar")
    return _salida(db, db.get(Reserva, reserva_id)), liberadas


# ----------------------------------------------------------------- CU13
def listar(db: Session, sucursal_id: int | None = None, estado: str | None = None) -> list[dict]:
    consulta = db.query(Reserva)
    if sucursal_id:
        consulta = consulta.filter(Reserva.sucursal_id == sucursal_id)
    if estado:
        if estado not in ESTADOS:
            raise HTTPException(400, f"Estado invalido. Use uno de: {', '.join(sorted(ESTADOS))}")
        consulta = consulta.filter(Reserva.estado == estado)
    # Para atender importa la hora de la cita: primero las mas proximas.
    filas = consulta.order_by(Reserva.fecha_hora_prueba.asc(), Reserva.id.asc()).all()
    return [_salida(db, r, con_cliente=True) for r in filas]


def preparar(db: Session, reserva_id: int) -> tuple[dict, int]:
    _existe(db, reserva_id)
    _cambiar_estado(db, reserva_id, {"pendiente"}, "preparada", liberar=False, verbo="preparar")
    return _salida(db, db.get(Reserva, reserva_id), con_cliente=True), 0


def atender(db: Session, reserva_id: int) -> tuple[dict, int]:
    _existe(db, reserva_id)
    # El cliente ya tiene las prendas en la mano: la reserva cumplio su funcion y
    # el stock deja de estar apartado. Si compra, la venta descuenta la cantidad.
    liberadas = _cambiar_estado(db, reserva_id, {"preparada"}, "atendida", liberar=True, verbo="atender")
    return _salida(db, db.get(Reserva, reserva_id), con_cliente=True), liberadas


def expirar(db: Session, reserva_id: int) -> tuple[dict, int]:
    _existe(db, reserva_id)
    liberadas = _cambiar_estado(db, reserva_id, ACTIVAS, "expirada", liberar=True, verbo="expirar")
    return _salida(db, db.get(Reserva, reserva_id), con_cliente=True), liberadas


# ---------------------------------------------------------------- internos
def _existe(db: Session, reserva_id: int) -> Reserva:
    reserva = db.get(Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(404, "Reserva no encontrada")
    return reserva


def _cambiar_estado(db: Session, reserva_id: int, desde: set[str], hacia: str,
                    liberar: bool, verbo: str) -> int:
    """Cambia el estado solo si esta en `desde`; devuelve las unidades liberadas."""
    resultado = db.execute(
        update(Reserva)
        .where(Reserva.id == reserva_id, Reserva.estado.in_(desde))
        .values(estado=hacia)
        .execution_options(synchronize_session=False)
    )
    if resultado.rowcount != 1:
        db.rollback()
        actual = db.get(Reserva, reserva_id)
        estado = actual.estado if actual else "desconocido"
        permitidos = " o ".join(f"'{e}'" for e in sorted(desde))
        raise HTTPException(
            400, f"No se puede {verbo} una reserva '{estado}': tiene que estar {permitidos}"
        )

    liberadas = _liberar(db, reserva_id) if liberar else 0
    db.commit()
    return liberadas


def _liberar(db: Session, reserva_id: int) -> int:
    """Devuelve al disponible lo que la reserva tenia apartado. No hace commit."""
    reserva = db.get(Reserva, reserva_id)
    detalles = (
        db.query(DetalleReserva)
        .filter(DetalleReserva.reserva_id == reserva_id, DetalleReserva.estado == "reservado")
        .all()
    )
    total = 0
    for d in detalles:
        db.execute(
            update(Inventario)
            .where(Inventario.variante_id == d.variante_id,
                   Inventario.sucursal_id == reserva.sucursal_id)
            .values(cantidad_reservada=case(
                (Inventario.cantidad_reservada >= d.cantidad, Inventario.cantidad_reservada - d.cantidad),
                else_=0,
            ))
            .execution_options(synchronize_session=False)
        )
        d.estado = "liberado"
        total += d.cantidad
    return total


def liberar_stock(db: Session, reserva_id: int) -> int:
    """Libera lo que la reserva todavia retiene. Lo usa el cobro de una venta.

    Es seguro llamarlo dos veces: solo toca lineas en "reservado" y las deja en
    "liberado", asi que nunca devuelve al disponible unidades de otra reserva.
    No hace commit: queda en la transaccion de quien llama.
    """
    return _liberar(db, reserva_id)
