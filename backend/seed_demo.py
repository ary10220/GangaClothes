"""Datos de demostracion: una tienda que se ve real en la presentacion.

Lo llama seed.py. Todo es idempotente: se puede correr varias veces, y sobre una
base que ya tiene datos (la de produccion), sin duplicar nada:

- catalogos, prendas, variantes, promociones y oferta se buscan por nombre;
- el stock de una variante en una sucursal solo se crea si no existia;
- el historial de ventas y reservas se genera una unica vez (lo marca la cuenta
  de la clienta de demostracion: si ya tiene compras, no se vuelve a generar);
- los envios a domicilio llevan su propia marca (si ya hay algun envio, no se
  cargan), asi que aparecen tambien en una base que ya traia ese historial.

Las cantidades salen de un generador con semilla fija: dos corridas sobre una
base vacia dejan exactamente los mismos datos.

Las fotos estan en web/public/img/prendas (ver CREDITOS.md ahi mismo) y se
guardan como ruta relativa: la web las sirve desde su propio dominio.
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app.core.security import hash_password
from app.models.catalogo import Categoria, Coleccion, Color, Prenda, Talla, Temporada, Variante
from app.models.envios import Envio
from app.models.inventario import (Compra, DetalleCompra, Inventario, MovimientoInventario,
                                   ProductoProveedor, ProductoProveedorTemporada, Proveedor)
from app.models.sucursales import Ciudad, Sucursal
from app.models.usuarios import Cliente, Usuario
from app.models.ventas import (DetalleReserva, DetalleVenta, Pago, Promocion, PromocionPrenda,
                               Reserva, Venta)
from app.modules.auth.service import asignar_rol
from app.modules.envios import tarifa
from app.modules.promociones import service as promociones

UTC = timedelta(hours=4)  # Bolivia -> UTC
IMG = "/img/prendas/"
CENTAVO = Decimal("0.01")

# nombre, categoria, coleccion, genero, marca, precio, costo, foto, colores, sucursales, descripcion
PRENDAS = [
    ("Polera basica algodon", "Poleras", "Coleccion Verano", "unisex", "Ganga Basics", 79.90, 45.00,
     "polera-basica-blanca.jpg", ["Blanco", "Negro", "Gris"], ["Central", "Norte", "Cochabamba"],
     "Polera de algodon peinado 100%, corte recto y cuello redondo reforzado. La basica que combina con todo."),
    ("Polera estampada Original", "Poleras", "Coleccion Verano", "unisex", "Urban Llama", 119.90, 62.00,
     "polera-estampada-original.jpg", ["Beige", "Blanco"], ["Central", "Norte"],
     "Polera oversize con estampado serigrafiado al frente. Algodon grueso de 220 g."),
    ("Polera negra minimal", "Poleras", "Coleccion Urbana", "hombre", "Urban Llama", 99.90, 52.00,
     "polera-negra-minimal.jpg", ["Negro"], ["Central", "Cochabamba"],
     "Polera negra de corte regular con logo bordado en el pecho."),
    ("Pantalon jean clasico", "Pantalones", "Coleccion Urbana", "unisex", "Denim Sur", 189.90, 110.00,
     "jean-clasico.jpg", ["Azul", "Negro"], ["Central", "Norte", "Cochabamba"],
     "Jean de cinco bolsillos, tiro medio y pierna recta. Denim rigido de 12 oz."),
    ("Jean skinny rasgado", "Pantalones", "Coleccion Urbana", "mujer", "Denim Sur", 229.90, 128.00,
     "jean-skinny-rasgado.jpg", ["Azul"], ["Central", "Norte"],
     "Jean skinny elasticado con roturas en rodilla y parches bordados."),
    ("Pantalon jogger rosa palo", "Pantalones", "Coleccion Verano", "mujer", "Ganga Basics", 169.90, 92.00,
     "jogger-rosa-palo.jpg", ["Rosa", "Beige"], ["Norte", "Cochabamba"],
     "Jogger de tela fluida con bolsillos cargo y pretina elastica."),
    ("Vestido floral rojo", "Vestidos", "Coleccion Verano", "mujer", "Flor de Ceibo", 289.90, 155.00,
     "vestido-floral-rojo.jpg", ["Rojo"], ["Central", "Norte", "Cochabamba"],
     "Vestido cruzado con estampado floral, manga corta con volado y cinturon incluido."),
    ("Vestido largo de gala", "Vestidos", "Coleccion Fiesta", "mujer", "Flor de Ceibo", 459.90, 250.00,
     "vestido-largo-gala.jpg", ["Rojo", "Negro"], ["Central"],
     "Vestido largo de gasa con gran vuelo, escote halter y espalda descubierta."),
    ("Vestido blanco de verano", "Vestidos", "Coleccion Verano", "mujer", "Flor de Ceibo", 249.90, 130.00,
     "vestido-blanco-verano.jpg", ["Blanco"], ["Central", "Cochabamba"],
     "Vestido corto de hombros descubiertos con volados. Algodon liviano."),
    ("Chamarra de cuero negra", "Chamarras", "Coleccion Invierno Urbano", "unisex", "Ruta 7", 599.90, 340.00,
     "chamarra-cuero-negra.jpg", ["Negro"], ["Central", "Norte"],
     "Chamarra biker de cuero sintetico premium, cierres metalicos y forro interior."),
    ("Chamarra bomber terracota", "Chamarras", "Coleccion Invierno Urbano", "unisex", "Ruta 7", 349.90, 190.00,
     "chamarra-bomber-terracota.jpg", ["Terracota", "Negro"], ["Central", "Norte", "Cochabamba"],
     "Bomber liviana de tela satinada con punos y cuello de rib."),
    ("Parka verde militar", "Chamarras", "Coleccion Invierno Urbano", "hombre", "Ruta 7", 429.90, 245.00,
     "parka-verde-militar.jpg", ["Verde"], ["Norte", "Cochabamba"],
     "Parka impermeable con capucha, cuatro bolsillos frontales y cordon de ajuste."),
    ("Camisa denim estampada", "Camisas", "Coleccion Urbana", "hombre", "Denim Sur", 199.90, 105.00,
     "camisa-denim-estampada.jpg", ["Celeste"], ["Central", "Norte"],
     "Camisa de denim liviano con micro estampado y botones a presion."),
    ("Camisa blanca formal", "Camisas", "Coleccion Fiesta", "hombre", "Sastre & Co", 219.90, 115.00,
     "camisa-blanca-formal.jpg", ["Blanco", "Celeste"], ["Central", "Norte", "Cochabamba"],
     "Camisa de vestir de popelina, corte slim y cuello italiano."),
    ("Falda plisada negra", "Faldas", "Coleccion Urbana", "mujer", "Flor de Ceibo", 159.90, 80.00,
     "falda-plisada-negra.jpg", ["Negro"], ["Central", "Norte", "Cochabamba"],
     "Falda corta de tablas con pretina ancha y cierre invisible."),
    ("Falda midi beige", "Faldas", "Coleccion Verano", "mujer", "Flor de Ceibo", 179.90, 95.00,
     "falda-midi-beige.jpg", ["Beige", "Blanco"], ["Central", "Cochabamba"],
     "Falda midi asimetrica con volado, tela con caida y pretina elastica."),
]

COLORES = [("Negro", "#000000"), ("Blanco", "#FFFFFF"), ("Rojo", "#D62828"), ("Azul", "#1D3557"),
           ("Beige", "#E8DCC4"), ("Gris", "#9A9A9A"), ("Rosa", "#E8B4B8"), ("Verde", "#4B5D3A"),
           ("Celeste", "#8FB8DE"), ("Terracota", "#C4673F")]

# nombre, tipo, valor, desde (dias desde hoy), hasta, prendas, descripcion
PROMOCIONES = [
    ("Primavera en vestidos", "porcentaje", 20, -5, 25,
     ["Vestido floral rojo", "Vestido largo de gala", "Vestido blanco de verano"],
     "20% en toda la linea de vestidos por el cambio de temporada"),
    ("Jeans con Bs 40 de descuento", "monto", 40, -2, 12,
     ["Pantalon jean clasico", "Jean skinny rasgado"], "Bs 40 menos en cada jean"),
    ("Semana de poleras", "porcentaje", 15, -1, 6,
     ["Polera basica algodon", "Polera estampada Original", "Polera negra minimal"],
     "15% en poleras, solo esta semana"),
    ("Liquidacion de invierno", "porcentaje", 25, -40, -10,
     ["Chamarra de cuero negra", "Chamarra bomber terracota", "Parka verde militar"],
     "Remate de chamarras al cierre del invierno (ya vencida)"),
]

# proveedor -> (datos, cuenta, productos). Cada producto: nombre, categoria, precio, minimo,
# temporadas, detalle y la prenda del catalogo a la que corresponde (None = sin definir).
PROVEEDORES = [
    ({"nombre": "Textiles Andinos SRL", "nit": "1023456021", "contacto": "Ramiro Quispe",
      "telefono": "3-3456789", "email": "ventas@textilesandinos.bo",
      "direccion": "Parque Industrial, Mz. 12, Santa Cruz"},
     ("Ramiro", "Quispe", "proveedor@gangaclothes.com", "Proveedor123"),
     [("Polera algodon peinado 180 g", "Poleras", 38.00, 24, ["Primavera-Verano 2026"],
       "Cuello redondo, colores lisos. Tallas S a XL.", "Polera basica algodon"),
      ("Polera oversize 220 g para estampar", "Poleras", 52.00, 12, ["Primavera-Verano 2026"],
       "Lista para serigrafia o DTF.", "Polera estampada Original"),
      ("Jean clasico denim 12 oz", "Pantalones", 98.00, 12, ["Primavera-Verano 2026", "Otono-Invierno 2026"],
       "Cinco bolsillos, lavado medio u oscuro.", "Pantalon jean clasico"),
      ("Jean skinny elasticado", "Pantalones", 112.00, 12, ["Primavera-Verano 2026"], "Con o sin roturas.", "Jean skinny rasgado"),
      ("Camisa popelina slim", "Camisas", 96.00, 10, ["Primavera-Verano 2026", "Otono-Invierno 2026"],
       "Blanca o celeste, cuello italiano.", "Camisa blanca formal"),
      ("Jogger tela fluida", "Pantalones", 78.00, 12, ["Primavera-Verano 2026"], "Rosa palo, beige o negro.", None)]),
    ({"nombre": "Confecciones Oriente", "nit": "4567123019", "contacto": "Carla Justiniano",
      "telefono": "3-3321100", "email": "pedidos@confeccionesoriente.bo",
      "direccion": "Av. Virgen de Cotoca 2350, Santa Cruz"},
     ("Carla", "Justiniano", "oriente@gangaclothes.com", "Proveedor123"),
     [("Vestido floral cruzado", "Vestidos", 138.00, 6, ["Primavera-Verano 2026"], "Estampados surtidos.", "Vestido floral rojo"),
      ("Vestido largo de gasa", "Vestidos", 225.00, 4, ["Primavera-Verano 2026"], "Rojo, negro o esmeralda.", "Vestido largo de gala"),
      ("Falda plisada", "Faldas", 68.00, 10, ["Primavera-Verano 2026", "Otono-Invierno 2026"],
       "Negra, gris o cuadrille.", "Falda plisada negra"),
      ("Chamarra bomber satinada", "Chamarras", 165.00, 6, ["Otono-Invierno 2026"], "Con forro liviano.", "Chamarra bomber terracota"),
      ("Parka impermeable con capucha", "Chamarras", 215.00, 6, ["Otono-Invierno 2026"],
       "Verde militar o negra.", None)]),
]

# Donde esta cada sucursal en el mapa (CU29). Coordenadas reales, tomadas de
# OpenStreetMap: Santa Cruz de la Sierra y el Prado de Cochabamba. Son el punto
# desde el que sale el delivery y desde el que se mide la distancia.
COORDENADAS_SUCURSAL = {
    "Central": (-17.783400, -63.182100),      # casco viejo, plaza 24 de Septiembre
    "Norte": (-17.749800, -63.178700),        # Av. Banzer, 4to anillo
    "Cochabamba": (-17.386800, -66.158600),   # Av. Ballivian, El Prado
}

# Envios de demostracion: tres compras en linea que se entregan a domicilio, en
# estados distintos, para que el panel del encargado y el seguimiento del
# cliente tengan que mostrar desde el primer minuto de la demostracion.
# (cliente, sucursal, direccion, referencia, telefono, lat, lon, express, estado, minutos_atras)
ENVIOS = [
    (0, "Central", "Av. San Martin #455, Barrio Equipetrol", "Edificio Torre Azul, departamento 5B",
     "70011223", -17.767200, -63.189700, False, "entregado", 4320),
    (1, "Norte", "Av. Banzer, 6to anillo, Condominio Las Palmas", "Casa 14, porton blanco",
     "71234567", -17.730500, -63.175500, True, "en_camino", 55),
    (2, "Central", "Av. Paurito, Barrio La Cuchilla (Plan 3000)", "Al lado de la farmacia",
     "76543210", -17.825800, -63.109400, False, "pendiente", 25),
]

REPARTIDORES = ["Marcos Pena", "Luis Gutierrez", "Fabiola Aguilera"]

CLIENTES = [
    ("Sofia", "Rojas", "sofia@gangaclothes.com", "Cliente#2026", "7654321 SC", "M"),
    ("Diego", "Mendoza", "diego@gangaclothes.com", "Cliente#2026", "8123456 SC", "L"),
    ("Valeria", "Suarez", "valeria@gangaclothes.com", "Cliente#2026", "6987452 CB", "S"),
]


def envios_demo(db, rnd, sucursales, clientes, prendas) -> int:
    """Tres compras en linea entregadas a domicilio, en estados distintos (CU29).

    Van aparte del resto del historial y con su propia marca (si ya hay algun
    envio, no hace nada) para que tambien se carguen sobre una base que ya traia
    ventas de un ciclo anterior, que es el caso de la de produccion.

    El costo sale de la misma tarifa que usa el checkout: nada se calcula a
    mano para la demostracion.
    """
    if db.query(Envio).first():
        return 0

    ultimo = (db.query(Venta.nro_comprobante).filter(Venta.nro_comprobante.isnot(None))
              .order_by(Venta.nro_comprobante.desc()).first())
    nro = int(ultimo[0].split("-")[1]) if ultimo else 0
    promos = db.query(Promocion).all()
    alcance = {}
    for pp in db.query(PromocionPrenda).all():
        alcance.setdefault(pp.prenda_id, []).append(pp.promocion_id)

    ids_prendas = [p.id for p in prendas.values()]
    ahora = datetime.utcnow().replace(second=0, microsecond=0)
    creados = 0

    for i, (icliente, clave, direccion, referencia, telefono,
            lat, lon, express, estado, atras) in enumerate(ENVIOS):
        sucursal = sucursales[clave]
        candidatos = (
            db.query(Inventario, Variante, Prenda)
            .join(Variante, Variante.id == Inventario.variante_id)
            .join(Prenda, Prenda.id == Variante.prenda_id)
            .filter(Inventario.sucursal_id == sucursal.id, Prenda.id.in_(ids_prendas),
                    Inventario.cantidad - Inventario.cantidad_reservada > 2)
            .order_by(Inventario.id).all()
        )
        if not candidatos:
            continue

        momento = ahora - timedelta(minutes=atras)
        dia = (momento - UTC).date()          # el dia en Bolivia, para las promociones
        nro += 1
        numero = f"C-{nro:06d}"

        venta = Venta(cliente_id=clientes[icliente].id, sucursal_id=sucursal.id,
                      canal="web" if i % 2 == 0 else "movil", fecha=momento, estado="pagada",
                      tipo_entrega="delivery", subtotal=0, descuento=0, costo_envio=0, total=0,
                      nro_comprobante=numero)
        db.add(venta)
        db.flush()

        bruto, rebaja = Decimal("0"), Decimal("0")
        for inv, variante, prenda in rnd.sample(candidatos, k=min(len(candidatos), 2)):
            cantidad = rnd.choice([1, 1, 2])
            vigentes = [pr for pr in promos if pr.id in alcance.get(prenda.id, [])
                        and pr.activo is not False and pr.fecha_inicio <= dia <= pr.fecha_fin]
            calculo = promociones.aplicar(prenda.precio_venta, vigentes)
            importe = (calculo["precio_lista"] * cantidad).quantize(CENTAVO)
            descuento = (calculo["descuento"] * cantidad).quantize(CENTAVO)
            db.add(DetalleVenta(venta_id=venta.id, variante_id=variante.id, cantidad=cantidad,
                                precio_unitario=calculo["precio_lista"], descuento=descuento,
                                subtotal=importe - descuento,
                                promocion_id=calculo["promocion"].id if calculo["promocion"] else None))
            inv.cantidad -= cantidad
            bruto += importe
            rebaja += descuento
            db.add(MovimientoInventario(variante_id=variante.id, sucursal_id=inv.sucursal_id,
                                        usuario_id=None, tipo="salida", cantidad=cantidad,
                                        fecha=momento, motivo=f"Venta #{venta.id} ({numero})"))

        mercaderia = bruto - rebaja
        distancia = tarifa.distancia_km(sucursal.latitud, sucursal.longitud, lat, lon)
        cotizacion = tarifa.cotizar(distancia, mercaderia, express)
        costo = Decimal(str(cotizacion["costo_envio"]))
        minutos = cotizacion["minutos_estimados"]

        venta.subtotal, venta.descuento = bruto, rebaja
        venta.costo_envio = costo
        venta.total = mercaderia + costo      # total = subtotal - descuento + envio
        # Se alternan los dos metodos de la tienda en linea para que la
        # demostracion muestre tanto un cobro con tarjeta como uno con QR.
        if i % 2 == 0:
            metodo, pasarela = "tarjeta", "stripe"
            referencia = f"pi_test_{rnd.getrandbits(96):024x}"
        else:
            metodo, pasarela = "qr", "bcp_qr"
            referencia = f"SIM{rnd.getrandbits(40):010X}"
        db.add(Pago(venta_id=venta.id, metodo=metodo, pasarela=pasarela, monto=venta.total,
                    moneda="BOB", estado="exitoso", fecha=momento, referencia_externa=referencia))

        envio = Envio(venta_id=venta.id, direccion=direccion, latitud=lat, longitud=lon,
                      referencia=referencia, telefono_contacto=telefono,
                      distancia_km=Decimal(str(cotizacion["distancia_km"])), costo_envio=costo,
                      express=express, estado=estado, fecha_creacion=momento,
                      fecha_estimada=momento + timedelta(minutes=minutos))
        # Cada estado deja atras la hora de los pasos que ya ocurrieron: de ahi
        # sale la linea de tiempo del seguimiento.
        if estado in ("asignado", "en_camino", "entregado"):
            envio.repartidor = REPARTIDORES[i % len(REPARTIDORES)]
            envio.fecha_asignacion = momento + timedelta(minutes=10)
        if estado in ("en_camino", "entregado"):
            envio.fecha_salida = momento + timedelta(minutes=max(minutos // 2, 15))
        if estado == "entregado":
            envio.fecha_entrega = momento + timedelta(minutes=minutos + 6)
        db.add(envio)
        creados += 1

    db.flush()
    return creados


def cargar(db, get_or_create) -> dict:
    rnd = random.Random(2026)
    hoy = promociones.hoy_bolivia()
    admin = db.query(Usuario).filter(Usuario.email == "admin@gangaclothes.com").first()
    cajero = db.query(Usuario).filter(Usuario.email == "cajero@gangaclothes.com").first()
    encargado = db.query(Usuario).filter(Usuario.email == "encargado@gangaclothes.com").first()

    # ------------------------------------------------------ red de tiendas
    scz = get_or_create(Ciudad, nombre="Santa Cruz de la Sierra", defaults={"departamento": "Santa Cruz"})
    cbba = get_or_create(Ciudad, nombre="Cochabamba", defaults={"departamento": "Cochabamba"})
    sucursales = {
        "Central": get_or_create(Sucursal, nombre="Sucursal Central", defaults={
            "ciudad_id": scz.id, "direccion": "Av. Principal #123", "horario": "Lun-Sab 9:00-20:00"}),
        "Norte": get_or_create(Sucursal, nombre="Sucursal Norte", defaults={
            "ciudad_id": scz.id, "direccion": "Av. Banzer, 4to anillo", "telefono": "3-3445566",
            "horario": "Lun-Dom 10:00-21:00"}),
        "Cochabamba": get_or_create(Sucursal, nombre="Sucursal Cochabamba", defaults={
            "ciudad_id": cbba.id, "direccion": "Av. Ballivian (El Prado) #540", "telefono": "4-4251100",
            "horario": "Lun-Sab 9:30-20:30"}),
    }

    # Las sucursales del seed anterior no tenian punto en el mapa: sin el, la
    # tienda no puede calcular la distancia y solo ofrece retiro en sucursal.
    for clave, sucursal in sucursales.items():
        if sucursal.latitud is None or sucursal.longitud is None:
            sucursal.latitud, sucursal.longitud = COORDENADAS_SUCURSAL[clave]

    # ------------------------------------------------------ catalogos base
    tallas = [get_or_create(Talla, nombre=n, defaults={"orden": i})
              for i, n in enumerate(["S", "M", "L", "XL"], 1)]
    colores = {n: get_or_create(Color, nombre=n, defaults={"codigo_hex": h}) for n, h in COLORES}
    categorias = {n: get_or_create(Categoria, nombre=n, defaults={"descripcion": d}) for n, d in [
        ("Poleras", "Poleras y camisetas"), ("Pantalones", "Jeans, joggers y pantalones de tela"),
        ("Vestidos", "Vestidos casuales y de fiesta"), ("Chamarras", "Chamarras, parkas y abrigos"),
        ("Camisas", "Camisas casuales y formales"), ("Faldas", "Faldas cortas y midi")]}

    verano = get_or_create(Temporada, nombre="Primavera-Verano 2026")
    if verano.fecha_inicio is None:
        verano.fecha_inicio, verano.fecha_fin = date(2026, 9, 21), date(2027, 3, 20)
    invierno = get_or_create(Temporada, nombre="Otono-Invierno 2026", defaults={
        "fecha_inicio": date(2026, 3, 21), "fecha_fin": date(2026, 9, 20)})
    temporadas = {t.nombre: t for t in (verano, invierno)}
    colecciones = {
        "Coleccion Verano": get_or_create(Coleccion, nombre="Coleccion Verano",
                                          defaults={"temporada_id": verano.id, "anio": 2026}),
        "Coleccion Urbana": get_or_create(Coleccion, nombre="Coleccion Urbana", defaults={
            "temporada_id": verano.id, "anio": 2026, "descripcion": "Basicos de calle para todo el ano"}),
        "Coleccion Fiesta": get_or_create(Coleccion, nombre="Coleccion Fiesta", defaults={
            "temporada_id": verano.id, "anio": 2026, "descripcion": "Para fiestas de fin de ano y graduaciones"}),
        "Coleccion Invierno Urbano": get_or_create(Coleccion, nombre="Coleccion Invierno Urbano", defaults={
            "temporada_id": invierno.id, "anio": 2026, "descripcion": "Abrigo para los surazos"}),
    }

    # ------------------------------------- prendas, variantes y stock inicial
    # El stock inicial entra con fecha de hace 60 dias: el historial de ventas
    # que se genera mas abajo sale de esas unidades.
    apertura = datetime.combine(hoy - timedelta(days=60), time(9, 0)) + UTC
    prendas = {}
    stock_nuevo = 0
    for (nombre, cat, colec, genero, marca, precio, costo, foto, cols, sucs, descripcion) in PRENDAS:
        p = get_or_create(Prenda, nombre=nombre, defaults={
            "categoria_id": categorias[cat].id, "coleccion_id": colecciones[colec].id,
            "precio_venta": precio, "costo": costo, "genero": genero, "publicado": True})
        # Las prendas del seed anterior no traian foto, marca ni descripcion.
        p.imagen_url = p.imagen_url if (p.imagen_url or "").startswith(IMG) else IMG + foto
        p.marca = p.marca or marca
        p.descripcion = p.descripcion or descripcion
        prendas[nombre] = p
        for t in tallas:
            for c in cols:
                color = colores[c]
                v = get_or_create(Variante, prenda_id=p.id, talla_id=t.id, color_id=color.id,
                                  defaults={"sku": f"P{p.id}-T{t.id}-C{color.id}"})
                for s in sucs:
                    sucursal = sucursales[s]
                    existe = (db.query(Inventario)
                              .filter(Inventario.variante_id == v.id, Inventario.sucursal_id == sucursal.id)
                              .first())
                    # La tirada se hace siempre, exista o no: asi la secuencia del
                    # generador no depende de lo que ya habia en la base.
                    cantidad = rnd.choice([6, 8, 8, 10, 10, 12, 14, 16])
                    if s != "Central":
                        cantidad = max(4, cantidad - rnd.choice([0, 2, 4]))
                    if t.nombre == "XL":
                        cantidad = max(4, cantidad - 3)
                    if existe:
                        continue
                    db.add(Inventario(variante_id=v.id, sucursal_id=sucursal.id, cantidad=cantidad,
                                      cantidad_reservada=0, stock_minimo=3, stock_maximo=20))
                    db.add(MovimientoInventario(variante_id=v.id, sucursal_id=sucursal.id,
                                                usuario_id=admin.id if admin else None, tipo="ingreso",
                                                cantidad=cantidad, motivo="Stock inicial", fecha=apertura))
                    stock_nuevo += 1
    db.flush()

    # --------------------------------------------------------- promociones
    for nombre, tipo, valor, desde, hasta, nombres, descripcion in PROMOCIONES:
        promo = get_or_create(Promocion, nombre=nombre, defaults={
            "descripcion": descripcion, "tipo_descuento": tipo, "valor": valor,
            "fecha_inicio": hoy + timedelta(days=desde), "fecha_fin": hoy + timedelta(days=hasta),
            "activo": True})
        for n in nombres:
            get_or_create(PromocionPrenda, promocion_id=promo.id, prenda_id=prendas[n].id)
    db.flush()

    # ------------------------------------------ proveedores con su oferta (CU9)
    for datos, (nombre, apellido, email, clave), productos in PROVEEDORES:
        prov = get_or_create(Proveedor, nombre=datos["nombre"],
                             defaults={k: v for k, v in datos.items() if k != "nombre"})
        u = get_or_create(Usuario, email=email, defaults={
            "nombre": nombre, "apellido": apellido, "password_hash": hash_password(clave)})
        asignar_rol(db, u.id, "proveedor")
        if prov.usuario_id is None:
            prov.usuario_id = u.id
        for i, (pnombre, cat, precio, minimo, temps, descripcion, prenda) in enumerate(productos):
            prod = get_or_create(ProductoProveedor, proveedor_id=prov.id, nombre=pnombre, defaults={
                "categoria_id": categorias[cat].id, "descripcion": descripcion,
                "prenda_id": prendas[prenda].id if prenda else None,
                "precio_referencial": precio, "cantidad_minima": minimo, "disponible": True,
                "fecha_actualizacion": datetime.utcnow() - timedelta(days=2 + i)})
            for t in temps:
                get_or_create(ProductoProveedorTemporada, producto_id=prod.id,
                              temporada_id=temporadas[t].id)
    db.flush()

    # ------------------------------------------------------------ clientes
    clientes = []
    for nombre, apellido, email, clave, ci, talla in CLIENTES:
        u = get_or_create(Usuario, email=email, defaults={
            "nombre": nombre, "apellido": apellido, "password_hash": hash_password(clave)})
        asignar_rol(db, u.id, "cliente")
        clientes.append(get_or_create(Cliente, usuario_id=u.id,
                                      defaults={"nit_ci": ci, "talla_preferida": talla}))
    db.flush()

    resumen = {"prendas": len(prendas), "stock_nuevo": stock_nuevo, "ventas": 0,
               "reservas": 0, "envios": 0}
    # Los envios de demostracion llevan su propia marca (ver `envios_demo`), asi
    # que se cargan igual sobre una base recien creada que sobre una que ya
    # traia el historial de ventas de otro ciclo, como la de produccion.
    def con_envios() -> dict:
        resumen["envios"] = envios_demo(db, rnd, sucursales, clientes, prendas)
        resumen["ventas"] += resumen["envios"]
        return resumen

    if db.query(Venta).filter(Venta.cliente_id == clientes[0].id).first():
        return con_envios()  # el historial ya se genero en una corrida anterior

    # ------------------------------------------------- historial de ventas
    ultimo = db.query(Venta.nro_comprobante).filter(Venta.nro_comprobante.isnot(None)) \
               .order_by(Venta.nro_comprobante.desc()).first()
    nro = int(ultimo[0].split("-")[1]) if ultimo else 0

    # Lo que se puede vender en cada sucursal: (inventario, variante, prenda)
    por_sucursal = {}
    for clave, s in sucursales.items():
        por_sucursal[clave] = (
            db.query(Inventario, Variante, Prenda)
            .join(Variante, Variante.id == Inventario.variante_id)
            .join(Prenda, Prenda.id == Variante.prenda_id)
            .filter(Inventario.sucursal_id == s.id, Prenda.id.in_([p.id for p in prendas.values()]))
            .order_by(Inventario.id).all()
        )
    promos = db.query(Promocion).all()
    alcance = {}
    for pp in db.query(PromocionPrenda).all():
        alcance.setdefault(pp.prenda_id, []).append(pp.promocion_id)

    def promos_del_dia(prenda_id: int, dia: date):
        ids = alcance.get(prenda_id, [])
        return [pr for pr in promos if pr.id in ids and pr.activo is not False
                and pr.fecha_inicio <= dia <= pr.fecha_fin]

    # Central vende mas; los fines de semana, tambien.
    plan = []
    for atras in range(45, 0, -1):
        dia = hoy - timedelta(days=atras)
        cuantas = rnd.choice([0, 1, 1, 2, 2, 3]) + (1 if dia.weekday() >= 5 else 0)
        for _ in range(cuantas):
            plan.append(dia)

    for dia in plan:
        clave = rnd.choices(["Central", "Norte", "Cochabamba"], weights=[5, 3, 2])[0]
        canal = rnd.choices(["caja", "web", "movil"], weights=[6, 3, 1])[0]
        candidatos = [f for f in por_sucursal[clave] if f[0].cantidad - f[0].cantidad_reservada > 2]
        if not candidatos:
            continue
        momento = datetime.combine(dia, time(rnd.randint(10, 19), rnd.choice([5, 12, 20, 34, 41, 52]))) + UTC
        venta = Venta(cliente_id=(rnd.choice(clientes).id if canal != "caja" or rnd.random() < 0.25 else None),
                      sucursal_id=sucursales[clave].id, cajero_id=cajero.id if canal == "caja" and cajero else None,
                      canal=canal, fecha=momento, estado="pagada", subtotal=0, descuento=0, total=0)
        db.add(venta)
        db.flush()
        bruto, rebaja = Decimal("0"), Decimal("0")
        for inv, variante, prenda in rnd.sample(candidatos, k=min(len(candidatos), rnd.choice([1, 1, 2, 2, 3]))):
            cantidad = rnd.choice([1, 1, 1, 2])
            calculo = promociones.aplicar(prenda.precio_venta, promos_del_dia(prenda.id, dia))
            importe = (calculo["precio_lista"] * cantidad).quantize(CENTAVO)
            descuento = (calculo["descuento"] * cantidad).quantize(CENTAVO)
            db.add(DetalleVenta(venta_id=venta.id, variante_id=variante.id, cantidad=cantidad,
                                precio_unitario=calculo["precio_lista"], descuento=descuento,
                                subtotal=importe - descuento,
                                promocion_id=calculo["promocion"].id if calculo["promocion"] else None))
            inv.cantidad -= cantidad
            bruto += importe
            rebaja += descuento
            nro_venta = nro + 1
            db.add(MovimientoInventario(variante_id=variante.id, sucursal_id=inv.sucursal_id,
                                        usuario_id=cajero.id if cajero else None, tipo="salida",
                                        cantidad=cantidad, fecha=momento,
                                        motivo=f"Venta #{venta.id} (C-{nro_venta:06d})"))
        nro += 1
        venta.subtotal, venta.descuento, venta.total = bruto, rebaja, bruto - rebaja
        venta.nro_comprobante = f"C-{nro:06d}"
        metodo = "pasarela" if canal != "caja" else rnd.choices(["efectivo", "qr", "tarjeta"], weights=[5, 3, 2])[0]
        recibido = venta.total
        if metodo == "efectivo":  # el cliente paga con billetes: se redondea hacia arriba a 10
            recibido = (venta.total / 10).to_integral_value(rounding="ROUND_CEILING") * 10
        db.add(Pago(venta_id=venta.id, metodo=metodo, pasarela="stripe" if metodo == "pasarela" else None,
                    monto=recibido, moneda="BOB", estado="exitoso", fecha=momento,
                    referencia_externa=f"pi_test_{rnd.getrandbits(96):024x}" if metodo == "pasarela" else None))
        resumen["ventas"] += 1
    db.flush()

    # --------------------------------------------- una compra ya recibida
    prov = db.query(Proveedor).filter(Proveedor.nombre == "Textiles Andinos SRL").first()
    fecha_compra = datetime.combine(hoy - timedelta(days=12), time(11, 30)) + UTC
    ofrecido = (db.query(ProductoProveedor)
                .filter(ProductoProveedor.proveedor_id == prov.id,
                        ProductoProveedor.nombre == "Polera algodon peinado 180 g").first())
    compra = Compra(proveedor_id=prov.id, sucursal_id=sucursales["Central"].id, fecha=fecha_compra,
                    estado="recibida", total=0)
    db.add(compra)
    db.flush()
    total = Decimal("0")
    for inv, variante, prenda in [f for f in por_sucursal["Central"]
                                  if f[2].nombre == "Polera basica algodon"][:4]:
        costo = Decimal(str(prenda.costo))
        db.add(DetalleCompra(compra_id=compra.id, variante_id=variante.id, cantidad=6,
                             producto_proveedor_id=ofrecido.id if ofrecido else None,
                             precio_unitario=costo, subtotal=costo * 6))
        inv.cantidad += 6
        total += costo * 6
        db.add(MovimientoInventario(variante_id=variante.id, sucursal_id=inv.sucursal_id,
                                    usuario_id=encargado.id if encargado else None, tipo="ingreso",
                                    cantidad=6, fecha=fecha_compra, motivo=f"Compra #{compra.id} a {prov.nombre}"))
    compra.total = total

    # ------------------------------------------------ historial de reservas
    def reservar(cliente, clave, cuando: datetime, estado: str, creada: datetime, notas=None):
        libres = [f for f in por_sucursal[clave] if f[0].cantidad - f[0].cantidad_reservada > 3]
        r = Reserva(cliente_id=cliente.id, sucursal_id=sucursales[clave].id, fecha_creacion=creada,
                    fecha_hora_prueba=cuando, estado=estado, notas=notas)
        db.add(r)
        db.flush()
        activa = estado in ("pendiente", "preparada")
        for inv, variante, _p in rnd.sample(libres, k=rnd.choice([1, 2, 2])):
            db.add(DetalleReserva(reserva_id=r.id, variante_id=variante.id, cantidad=1,
                                  estado="reservado" if activa else "liberado"))
            if activa:  # una reserva activa retiene unidades: no se pueden vender a otro
                inv.cantidad_reservada += 1
        resumen["reservas"] += 1

    ahora = datetime.now().replace(minute=0, second=0, microsecond=0)
    pasadas = [("atendida", 20), ("atendida", 14), ("cancelada", 11), ("atendida", 8),
               ("expirada", 6), ("atendida", 4), ("cancelada", 2)]
    for i, (estado, atras) in enumerate(pasadas):
        cuando = (ahora - timedelta(days=atras)).replace(hour=rnd.choice([11, 15, 17, 18]))
        reservar(clientes[i % 3], ["Central", "Norte", "Cochabamba"][i % 3], cuando, estado,
                 cuando - timedelta(days=1) + UTC)
    reservar(clientes[0], "Central", (ahora + timedelta(days=1)).replace(hour=16), "pendiente",
             datetime.utcnow() - timedelta(hours=5), "Quiero probarme tambien una talla mas")
    reservar(clientes[1], "Norte", (ahora + timedelta(days=2)).replace(hour=11), "preparada",
             datetime.utcnow() - timedelta(hours=20))
    reservar(clientes[2], "Cochabamba", (ahora + timedelta(days=1)).replace(hour=18), "pendiente",
             datetime.utcnow() - timedelta(hours=2))

    # Dos variantes quedan al limite para que se vea la alerta de stock minimo.
    for inv, _v, _p in por_sucursal["Norte"][:2]:
        sobra = inv.cantidad - inv.cantidad_reservada - 2
        if sobra > 0:
            inv.cantidad -= sobra
            db.add(MovimientoInventario(variante_id=inv.variante_id, sucursal_id=inv.sucursal_id,
                                        usuario_id=encargado.id if encargado else None, tipo="salida",
                                        cantidad=sobra, motivo="Prendas con falla retiradas de exhibicion",
                                        fecha=datetime.utcnow() - timedelta(days=3)))
    db.flush()
    return con_envios()
