"""Comprobante de venta en PDF (CU15).

Toma el diccionario que arma `ventas/service.comprobante()` y lo dibuja. Es el
mismo documento para una venta en caja y para una compra web: lo unico que
cambia es el canal, el cajero y el metodo de pago.

Se dibuja "a mano" con el canvas de ReportLab en lugar de usar Platypus porque
el ticket es una sola pagina de estructura fija: sale mas corto de leer y el
control del alto de cada bloque es exacto.

Formato carta (21,6 x 27,9 cm), que es lo que hay en cualquier impresora de
oficina. Un ticket termico de 80 mm seria otra plantilla, no otro modulo.
"""
import io

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

ANCHO, ALTO = letter
MARGEN = 18 * mm

TINTA = HexColor("#1f2937")      # gris muy oscuro para el texto
SUAVE = HexColor("#6b7280")      # gris medio para etiquetas
LINEA = HexColor("#d1d5db")
ACENTO = HexColor("#111827")
FONDO_FILA = HexColor("#f3f4f6")
VERDE = HexColor("#047857")

# Columnas de la tabla de prendas. Todas menos la descripcion se alinean a la
# derecha, que es donde cae el ultimo digito de cada importe.
COL_DESC = MARGEN
COL_TOTAL = ANCHO - MARGEN
COL_DESC_BS = COL_TOTAL - 30 * mm
COL_PRECIO = COL_DESC_BS - 26 * mm
COL_CANT = COL_PRECIO - 24 * mm
ANCHO_DESC = COL_CANT - COL_DESC - 8 * mm

# Alto de una fila: la linea del importe mas la del SKU (y la promocion).
ALTO_LINEA = 13
ALTO_DETALLE = 11


def _bs(valor) -> str:
    """350.5 -> 'Bs 350,50'. Separador de miles punto y decimal coma, como se
    escriben los importes en Bolivia; siempre con los dos decimales."""
    entero, _, decimales = f"{float(valor or 0):,.2f}".partition(".")
    return f"Bs {entero.replace(',', '.')},{decimales}"


def _recortar(c: rl_canvas.Canvas, texto: str, ancho: float, fuente: str, tamano: float) -> str:
    """Corta el texto con puntos suspensivos para que nunca pise la columna siguiente."""
    texto = texto or ""
    if c.stringWidth(texto, fuente, tamano) <= ancho:
        return texto
    while texto and c.stringWidth(texto + "...", fuente, tamano) > ancho:
        texto = texto[:-1]
    return texto + "..."


def _titulo(c: rl_canvas.Canvas, datos: dict, y: float) -> float:
    sucursal = datos.get("sucursal") or {}

    c.setFillColor(ACENTO)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(MARGEN, y, datos.get("tienda") or "GANGACLOTHES")

    c.setFont("Helvetica", 8.5)
    c.setFillColor(SUAVE)
    y -= 13
    for linea in (
        sucursal.get("nombre"),
        ", ".join(filter(None, [sucursal.get("direccion"), sucursal.get("ciudad")])) or None,
        f"Tel. {sucursal['telefono']}" if sucursal.get("telefono") else None,
    ):
        if linea:
            c.drawString(MARGEN, y, linea)
            y -= 11

    # Bloque derecho: numero de comprobante, fecha y canal.
    tope = ALTO - MARGEN
    c.setFillColor(SUAVE)
    c.setFont("Helvetica", 8.5)
    c.drawRightString(ANCHO - MARGEN, tope, "COMPROBANTE DE VENTA")
    c.setFillColor(ACENTO)
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(ANCHO - MARGEN, tope - 18, datos.get("nro_comprobante") or "—")
    c.setFillColor(SUAVE)
    c.setFont("Helvetica", 8.5)
    c.drawRightString(ANCHO - MARGEN, tope - 32, datos.get("fecha_bolivia") or "")
    canal = (datos.get("canal") or "").upper()
    etiqueta_canal = {"CAJA": "Venta en caja", "WEB": "Compra en linea",
                      "MOVIL": "Compra desde la app"}.get(canal, canal)
    c.drawRightString(ANCHO - MARGEN, tope - 43, f"{etiqueta_canal} · Venta #{datos.get('venta_id')}")

    return min(y, tope - 52) - 8


def _regla(c: rl_canvas.Canvas, y: float) -> float:
    c.setStrokeColor(LINEA)
    c.setLineWidth(0.7)
    c.line(MARGEN, y, ANCHO - MARGEN, y)
    return y - 14


def _partes(c: rl_canvas.Canvas, datos: dict, y: float) -> float:
    """Cliente a la izquierda, quien atendio a la derecha."""
    cliente = datos.get("cliente") or {}
    cajero = datos.get("cajero") or {}

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(SUAVE)
    c.drawString(MARGEN, y, "CLIENTE")
    c.drawString(ANCHO / 2, y, "ATENDIDO POR")
    y -= 12

    c.setFont("Helvetica", 9.5)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, y, cliente.get("nombre") or "Consumidor final")
    c.drawString(ANCHO / 2, y, cajero.get("nombre") or "Tienda en linea")
    if cliente.get("email"):
        y -= 11
        c.setFont("Helvetica", 8.5)
        c.setFillColor(SUAVE)
        c.drawString(MARGEN, y, cliente["email"])
    return y - 16


def _cabecera_tabla(c: rl_canvas.Canvas, y: float) -> float:
    c.setFillColor(SUAVE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(COL_DESC, y, "PRENDA / TALLA · COLOR")
    c.drawRightString(COL_CANT, y, "CANT.")
    c.drawRightString(COL_PRECIO, y, "P. UNIT.")
    c.drawRightString(COL_DESC_BS, y, "DESC.")
    c.drawRightString(COL_TOTAL, y, "SUBTOTAL")
    return _regla(c, y - 6)


def _items(c: rl_canvas.Canvas, datos: dict, y: float) -> float:
    """Una fila por prenda: importes arriba, SKU y promocion en letra chica debajo.

    El alto se calcula antes de dibujar el fondo, para que la banda gris cubra
    exactamente su fila y no invada la siguiente.
    """
    for i, item in enumerate(datos.get("items") or []):
        alto = ALTO_LINEA + ALTO_DETALLE
        if i % 2 == 0:
            c.setFillColor(FONDO_FILA)
            c.rect(MARGEN - 4, y - alto + ALTO_LINEA - 4, ANCHO - 2 * MARGEN + 8, alto, stroke=0, fill=1)

        c.setFillColor(TINTA)
        c.setFont("Helvetica", 9.5)
        c.drawString(COL_DESC, y, _recortar(c, item.get("descripcion", ""), ANCHO_DESC, "Helvetica", 9.5))
        c.drawRightString(COL_CANT, y, str(item.get("cantidad", "")))
        c.drawRightString(COL_PRECIO, y, _bs(item.get("precio_unitario")))
        descuento = float(item.get("descuento") or 0)
        c.setFillColor(VERDE if descuento else SUAVE)
        c.drawRightString(COL_DESC_BS, y, f"-{_bs(descuento)}" if descuento else "—")
        c.setFillColor(TINTA)
        c.drawRightString(COL_TOTAL, y, _bs(item.get("subtotal")))

        y -= ALTO_LINEA
        c.setFont("Helvetica", 7.5)
        c.setFillColor(SUAVE)
        detalle = f"SKU {item.get('sku', '')}"
        if item.get("promocion"):
            detalle += f"   ·   Promocion aplicada: {item['promocion']}"
        c.drawString(COL_DESC, y, detalle)
        y -= ALTO_DETALLE

    return y - 4


def _totales(c: rl_canvas.Canvas, datos: dict, y: float) -> float:
    y = _regla(c, y)
    izquierda = ANCHO - MARGEN - 62 * mm

    def fila(etiqueta: str, valor: str, negrita: bool = False, color=TINTA) -> None:
        nonlocal y
        c.setFont("Helvetica-Bold" if negrita else "Helvetica", 10.5 if negrita else 9.5)
        c.setFillColor(SUAVE if not negrita else color)
        c.drawString(izquierda, y, etiqueta)
        c.setFillColor(color)
        c.drawRightString(COL_TOTAL, y, valor)
        y -= 15

    fila("Subtotal", _bs(datos.get("subtotal")))
    descuento = float(datos.get("descuento") or 0)
    if descuento:
        fila("Descuentos aplicados", f"-{_bs(descuento)}", color=VERDE)
    # CU29: el envio se cobra aparte de la mercaderia y se ve como tal.
    if datos.get("entrega"):
        envio = float(datos.get("costo_envio") or 0)
        express = " (express)" if datos["entrega"].get("express") else ""
        if envio:
            fila(f"Envio a domicilio{express}", _bs(envio))
        else:
            fila(f"Envio a domicilio{express}", "GRATIS", color=VERDE)

    y -= 2
    c.setStrokeColor(ACENTO)
    c.setLineWidth(1.1)
    c.line(izquierda, y + 9, ANCHO - MARGEN, y + 9)
    y -= 6
    fila("TOTAL", _bs(datos.get("total")), negrita=True, color=ACENTO)
    return y - 4


def _pago(c: rl_canvas.Canvas, datos: dict, y: float) -> float:
    pago = datos.get("pago") or {}
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(SUAVE)
    c.drawString(MARGEN, y, "FORMA DE PAGO")
    y -= 13

    c.setFont("Helvetica", 9.5)
    c.setFillColor(TINTA)
    c.drawString(MARGEN, y, pago.get("etiqueta") or pago.get("metodo") or "—")
    y -= 12

    c.setFont("Helvetica", 8.5)
    c.setFillColor(SUAVE)
    if pago.get("metodo") == "efectivo":
        c.drawString(MARGEN, y, f"Recibido {_bs(pago.get('recibido'))}  ·  "
                                f"Cambio {_bs(pago.get('cambio'))}")
        y -= 11
    if pago.get("referencia_externa"):
        c.drawString(MARGEN, y, f"Referencia: {pago['referencia_externa']}")
        y -= 11
    return y


def _entrega(c: rl_canvas.Canvas, datos: dict, y: float) -> float:
    """Columna derecha del pie: a donde se llevo el pedido (CU29).

    Solo aparece en las compras con delivery. En retiro en sucursal el ticket
    queda exactamente igual que antes de este ciclo.
    """
    entrega = datos.get("entrega")
    if not entrega:
        return y
    x = ANCHO / 2

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(SUAVE)
    c.drawString(x, y, "ENTREGA A DOMICILIO")
    y -= 13

    c.setFont("Helvetica", 9.5)
    c.setFillColor(TINTA)
    ancho = ANCHO - MARGEN - x
    c.drawString(x, y, _recortar(c, entrega.get("direccion") or "", ancho, "Helvetica", 9.5))
    y -= 12

    c.setFont("Helvetica", 8.5)
    c.setFillColor(SUAVE)
    for linea in (
        entrega.get("referencia"),
        f"Tel. {entrega['telefono']}" if entrega.get("telefono") else None,
        f"{entrega.get('distancia_km')} km desde la sucursal"
        + ("  ·  entrega express" if entrega.get("express") else ""),
        f"Repartidor: {entrega['repartidor']}" if entrega.get("repartidor") else None,
    ):
        if linea:
            c.drawString(x, y, _recortar(c, str(linea), ancho, "Helvetica", 8.5))
            y -= 11
    return y


def _pie(c: rl_canvas.Canvas, datos: dict) -> None:
    y = MARGEN + 18
    c.setStrokeColor(LINEA)
    c.setLineWidth(0.7)
    c.line(MARGEN, y + 14, ANCHO - MARGEN, y + 14)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(SUAVE)
    c.drawString(MARGEN, y, "Gracias por su compra. Este comprobante respalda la entrega de las "
                            "prendas detalladas.")
    y -= 10
    reserva = f"  ·  Reserva #{datos['reserva_id']}" if datos.get("reserva_id") else ""
    c.drawString(MARGEN, y, f"GangaClothes · Documento generado el {datos.get('fecha_bolivia', '')} "
                            f"(hora de Bolivia){reserva}")


def generar(datos: dict) -> bytes:
    """Devuelve el PDF del comprobante listo para imprimir o descargar."""
    memoria = io.BytesIO()
    c = rl_canvas.Canvas(memoria, pagesize=letter)
    c.setTitle(f"Comprobante {datos.get('nro_comprobante') or ''}".strip())
    c.setAuthor("GangaClothes")
    c.setSubject(f"Venta #{datos.get('venta_id')}")

    y = _titulo(c, datos, ALTO - MARGEN)
    y = _regla(c, y)
    y = _partes(c, datos, y)
    y = _cabecera_tabla(c, y)
    y = _items(c, datos, y)
    y = _totales(c, datos, y)
    _pago(c, datos, y - 6)
    _entrega(c, datos, y - 6)
    _pie(c, datos)

    c.showPage()
    c.save()
    return memoria.getvalue()


def nombre_archivo(datos: dict) -> str:
    numero = (datos.get("nro_comprobante") or f"venta-{datos.get('venta_id')}").replace("/", "-")
    return f"comprobante-{numero}.pdf"
