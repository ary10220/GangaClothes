"""El asistente (CU28): memoria de la conversacion y orquestacion.

El ciclo de un mensaje:

    1. se guarda lo que escribio la persona
    2. se le manda al modelo la conversacion + las herramientas de su rol
    3. si el modelo pide datos, se ejecuta la herramienta y se le devuelven
       (hasta `IA_MAX_PASOS` veces, para que no quede dando vueltas)
    4. se guarda la respuesta y se devuelve, junto con las prendas que salieron
       para que la pantalla las muestre como tarjetas

Lo que hace que se sienta una conversacion y no un formulario:

* **Memoria.** Cada turno viaja con los anteriores, asi "¿y en negro?" se
  entiende sin repetir la pregunta entera.
* **Pregunta en vez de adivinar.** Se lo pide la instruccion del sistema; no hay
  ningun `if` que lo fuerce, por eso puede decidir cuando le alcanza lo que sabe.
* **No inventa.** Solo puede nombrar lo que devolvieron las herramientas.

Y si falta la clave o Google no responde, el asistente **no se cae**: contesta
en modo sin modelo, usando las mismas herramientas. Es mas seco, pero funciona.
"""
import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.fechas import hoy_bolivia, utc_iso
from app.models.ia import Conversacion, MensajeChat
from app.models.usuarios import Cliente, Usuario
from app.modules.ia import gemini, herramientas, recomendador

MAX_MENSAJE = 1000


# ================================================================== contexto
def contexto(db: Session, usuario: Usuario, personal: bool,
             sucursal_id: int | None = None) -> dict:
    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
    return {
        "usuario": usuario,
        "cliente": cliente,
        "personal": personal,
        "es_cliente": cliente is not None,
        "sucursal_id": sucursal_id,
    }


def _nombre(usuario: Usuario) -> str:
    return (usuario.nombre or "").strip() or usuario.email.split("@")[0]


def instrucciones(db: Session, ctx: dict) -> str:
    """La instruccion del sistema: quien es, que puede decir y como habla."""
    hoy = hoy_bolivia().strftime("%d/%m/%Y")
    persona = _nombre(ctx["usuario"])

    comunes = f"""Hoy es {hoy} (hora de Bolivia). Los precios estan en bolivianos (Bs).

REGLAS QUE NO PODES ROMPER:
- Solo podes nombrar prendas, precios, stock y cifras que hayan salido de una
  herramienta en esta misma conversacion. Nunca inventes ni completes de memoria.
- Si una herramienta devuelve cantidad 0, decilo con todas las letras y ofrece
  lo que si hay, usando la informacion que la propia herramienta te dio.
- Si no estas seguro de algo, preguntá o consultá la herramienta otra vez.
  Nunca respondas "creo que" sobre un dato.
- No prometas hacer cosas que no podes: en esta version solo consultas. Si te
  piden agregar al carrito, reservar o comprar, explica en una linea donde
  hacerlo en la tienda.

COMO HABLAS:
- En castellano, de vos, cercano pero sin exagerar. Nada de "estimado cliente".
- Corto: dos a cuatro frases. Si tenes que listar prendas, maximo cinco, cada
  una con su precio.
- No uses tablas ni encabezados; es una conversacion por chat."""

    if ctx["personal"]:
        return f"""Sos el analista de datos de GangaClothes, una tienda de ropa en Bolivia.
Estas hablando con {persona}, que trabaja en la tienda.

Tu trabajo es responder preguntas sobre el negocio con los numeros reales:
ventas, inventario, ganancia, reposicion y desempeno del recomendador.

{comunes}

ADEMAS, COMO ANALISTA:
- Dá el numero primero y despues la lectura. "Bs 31.093 en 31 dias, 124% mas que
  el periodo anterior" antes que "las ventas vienen muy bien".
- Cuando veas algo que llame la atencion (una sucursal que cae, una prenda sin
  stock, un margen bajo), mencionalo aunque no te lo hayan preguntado.
- Si no te aclaran el periodo, usa los ultimos 30 dias y decí cual usaste."""

    return f"""Sos el asistente de compras de GangaClothes, una tienda de ropa en Bolivia.
Estas atendiendo a {persona}, que es cliente.

Tu trabajo es ayudarle a encontrar ropa que le sirva y contarle sobre sus
compras, sus reservas y las promociones vigentes.

{comunes}

ADEMAS, COMO VENDEDOR:
- Si te piden algo vago ("busco algo lindo", "para una fiesta"), preguntá UNA
  sola cosa que te ayude a buscar mejor: la ocasion, el presupuesto, la talla o
  el color. Una por mensaje, no un interrogatorio.
- Si ya sabes lo suficiente, buscá y mostrá; no sigas preguntando de gusto.
- Cuando te pidan recomendaciones, usa `recomendar_para_mi`: ese es el
  recomendador de la tienda y ya sabe que compro esta persona. No elijas vos.
- Si una prenda viene con `por_que_se_sugiere`, contá ese motivo con tus
  palabras: al cliente le gusta saber por que se la estas mostrando."""


# ============================================================== conversacion
def _conversacion(db: Session, usuario: Usuario, conversacion_id: int | None,
                  origen: str | None) -> Conversacion:
    if conversacion_id is not None:
        conversacion = db.get(Conversacion, conversacion_id)
        if conversacion is None or conversacion.usuario_id != usuario.id:
            raise HTTPException(404, "Esa conversacion no existe o no es tuya")
        return conversacion
    conversacion = Conversacion(usuario_id=usuario.id, origen=origen)
    db.add(conversacion)
    db.commit()
    return conversacion


def _guardar(db: Session, conversacion: Conversacion, rol: str, texto: str | None,
             herramienta: str | None = None, argumentos: dict | None = None) -> MensajeChat:
    mensaje = MensajeChat(
        conversacion_id=conversacion.id, rol=rol, texto=texto, herramienta=herramienta,
        argumentos=json.dumps(argumentos, ensure_ascii=False) if argumentos else None,
    )
    db.add(mensaje)
    db.commit()
    return mensaje


def _historial(db: Session, conversacion: Conversacion) -> list[dict]:
    """Los ultimos turnos, en el formato que espera el modelo.

    Solo van los de la persona y los del asistente: los resultados de las
    herramientas quedan guardados para auditar, pero no se le reenvian, porque
    ocuparian toda la memoria con datos que ya estan resumidos en la respuesta.
    """
    filas = (
        db.query(MensajeChat)
        .filter(MensajeChat.conversacion_id == conversacion.id,
                MensajeChat.rol.in_(("usuario", "asistente")))
        .order_by(MensajeChat.id.desc())
        .limit(settings.ia_memoria_mensajes)
        .all()
    )
    return [gemini.turno_usuario(m.texto) if m.rol == "usuario" else gemini.turno_modelo(m.texto)
            for m in reversed(filas) if m.texto]


# ================================================================ el mensaje
def chat(db: Session, usuario: Usuario, mensaje: str, personal: bool, *,
         conversacion_id: int | None = None, origen: str | None = None,
         sucursal_id: int | None = None) -> dict:
    texto = (mensaje or "").strip()
    if not texto:
        raise HTTPException(400, "El mensaje esta vacio")
    if len(texto) > MAX_MENSAJE:
        raise HTTPException(400, f"El mensaje es muy largo (maximo {MAX_MENSAJE} caracteres)")

    ctx = contexto(db, usuario, personal, sucursal_id)
    if not ctx["es_cliente"] and not personal:
        raise HTTPException(403, "Tu cuenta no tiene acceso al asistente")

    conversacion = _conversacion(db, usuario, conversacion_id, origen)
    _guardar(db, conversacion, "usuario", texto)
    if not conversacion.titulo:
        conversacion.titulo = texto[:80]
        db.commit()

    caja = herramientas.disponibles(personal=personal, es_cliente=ctx["es_cliente"])
    historial = _historial(db, conversacion)

    if gemini.disponible():
        try:
            salida = _con_modelo(db, ctx, caja, conversacion, historial)
        except gemini.ErrorIA as e:
            # El modelo fallo, pero las herramientas estan: se responde igual.
            salida = _sin_modelo(db, ctx, caja, texto)
            salida["aviso"] = f"El asistente respondio sin el modelo de lenguaje ({e})."
    else:
        salida = _sin_modelo(db, ctx, caja, texto)

    _guardar(db, conversacion, "asistente", salida["respuesta"])
    conversacion.actualizada = None  # que lo ponga la base
    db.commit()

    return {
        "conversacion_id": conversacion.id,
        "titulo": conversacion.titulo,
        **salida,
    }


def _con_modelo(db: Session, ctx: dict, caja: dict, conversacion: Conversacion,
                historial: list[dict]) -> dict:
    """Va y vuelve con el modelo hasta que deje de pedir datos."""
    declaraciones = herramientas.declaraciones(caja)
    sistema = instrucciones(db, ctx)
    contenidos = list(historial)
    consultas, prendas = [], []

    for _paso in range(settings.ia_max_pasos):
        respuesta = gemini.responder(sistema, contenidos, declaraciones)
        if not respuesta["llamadas"]:
            return {
                "respuesta": respuesta["texto"] or "No se me ocurre que responder a eso.",
                "modo": "gemini",
                "consultas": consultas,
                "prendas": prendas,
            }

        # El turno del modelo vuelve SIN TOCAR: trae la firma de cada llamada y
        # el servidor la exige de vuelta (ver gemini.responder).
        contenidos.append(respuesta["contenido"])
        resultados = []
        for llamada in respuesta["llamadas"]:
            nombre, argumentos = llamada["nombre"], llamada["argumentos"]
            resultado = herramientas.ejecutar(db, ctx, caja, nombre, argumentos)
            _guardar(db, conversacion, "herramienta",
                     json.dumps(resultado, ensure_ascii=False, default=str)[:4000],
                     herramienta=nombre, argumentos=argumentos)
            consultas.append({"herramienta": nombre, "argumentos": argumentos,
                              "resultados": resultado.get("cantidad")})
            prendas.extend(_prendas_de(resultado))
            resultados.append((nombre, resultado))
        contenidos.append(gemini.turno_resultados(resultados))

    # Se acabaron los pasos: se le pide que cierre con lo que ya tiene.
    cierre = gemini.responder(sistema + "\n\nYa tenes todos los datos: responde ahora, sin pedir mas.",
                              contenidos, [])
    return {
        "respuesta": cierre["texto"] or "Consulte los datos pero no pude armar la respuesta.",
        "modo": "gemini",
        "consultas": consultas,
        "prendas": prendas,
    }


def _prendas_de(resultado: dict) -> list[dict]:
    """Las prendas que salieron de una herramienta, para pintarlas como tarjetas."""
    filas = resultado.get("resultados")
    if not isinstance(filas, list):
        return []
    return [f for f in filas if isinstance(f, dict) and "nombre" in f and "precio" in f]


# ========================================================== modo sin modelo
# Respaldo para cuando no hay clave o Google no contesta. Reconoce la intencion
# por palabras y responde con los datos tal cual. No conversa, pero no miente ni
# deja al usuario sin respuesta, que es lo que importa en una demostracion.
INTENCIONES_CLIENTE = [
    (("recomend", "sugier", "que me llevo", "no se que", "algo para mi", "ideas"), "recomendar_para_mi"),
    (("promo", "descuento", "oferta", "rebaj"), "promociones_vigentes"),
    (("mis compras", "compre", "mis pedidos", "comprobante"), "mis_compras"),
    (("reserva", "probador", "probarme"), "mis_reservas"),
]
INTENCIONES_PERSONAL = [
    (("stock bajo", "repon", "reposicion", "falta stock", "agotad"), "stock_bajo"),
    (("ganancia", "margen", "rentab", "utilidad"), "reporte_margen"),
    (("inventario", "valorizado"), "reporte_inventario"),
    (("recomendador", "efectividad"), "efectividad_recomendaciones"),
    (("venta", "vendi", "factur", "ingreso", "resumen", "como vamos"), "resumen_del_negocio"),
]


def _sin_modelo(db: Session, ctx: dict, caja: dict, texto: str) -> dict:
    minusculas = texto.lower()
    intenciones = INTENCIONES_PERSONAL if ctx["personal"] else INTENCIONES_CLIENTE

    for palabras, herramienta in intenciones:
        if herramienta in caja and any(p in minusculas for p in palabras):
            resultado = herramientas.ejecutar(db, ctx, caja, herramienta, {})
            return {"respuesta": _redactar(herramienta, resultado), "modo": "sin_modelo",
                    "consultas": [{"herramienta": herramienta, "argumentos": {}}],
                    "prendas": _prendas_de(resultado)}

    if "buscar_prendas" in caja:
        argumentos = _filtros_del_texto(db, ctx, minusculas)
        resultado = herramientas.ejecutar(db, ctx, caja, "buscar_prendas", argumentos)
        return {"respuesta": _redactar("buscar_prendas", resultado), "modo": "sin_modelo",
                "consultas": [{"herramienta": "buscar_prendas", "argumentos": argumentos}],
                "prendas": _prendas_de(resultado)}

    return {"respuesta": "Por ahora puedo buscar prendas, contarte las promociones y mostrarte "
                         "tus compras. ¿Que te gustaria ver?",
            "modo": "sin_modelo", "consultas": [], "prendas": []}


# Colores de uso corriente. No son el catalogo: sirven unicamente para darse
# cuenta de que el mensaje pide un color. Si el color pedido no existe en la
# tienda, la busqueda devuelve cero y se responde que no hay, en lugar de
# mostrar prendas de otro color como si fueran lo pedido.
COLORES_CONOCIDOS = (
    "negro", "blanco", "gris", "rojo", "azul", "celeste", "verde", "amarillo",
    "naranja", "rosa", "violeta", "morado", "lila", "fucsia", "beige", "crema",
    "marron", "cafe", "terracota", "dorado", "plateado", "turquesa", "vino",
    "bordo", "mostaza", "coral", "salmon",
)


def _raiz(palabra: str) -> str:
    """"Roja", "rojos", "rojo" -> "roj". Sirve para que el genero y el plural no
    hagan fallar la coincidencia: sin esto, "polera roja" no encuentra el color
    "Rojo" y se terminan mostrando poleras de cualquier color."""
    return palabra.lower().strip().rstrip("aeos") or palabra.lower().strip()


def _menciona(texto: str, valor: str) -> bool:
    """Si alguna palabra del texto comparte raiz con `valor`."""
    raiz = _raiz(valor)
    if len(raiz) < 3:
        return valor.lower() in texto
    return any(_raiz(palabra).startswith(raiz) or raiz.startswith(_raiz(palabra))
               for palabra in texto.split() if len(palabra) >= 3)


def _filtros_del_texto(db: Session, ctx: dict, texto: str) -> dict:
    """Saca color, talla y categoria del mensaje comparando contra el catalogo real.

    Se compara contra lo que existe de verdad (no contra una lista escrita a
    mano), asi que una categoria o un color nuevos funcionan sin tocar nada.
    """
    items = recomendador.catalogo(db, sucursal_id=ctx.get("sucursal_id"))
    filtros: dict = {}

    for categoria in sorted({i["categoria"] for i in items if i.get("categoria")}):
        if _menciona(texto, categoria):
            filtros["categoria"] = categoria
            break
    colores_con_stock = sorted({c for i in items for c in (i.get("colores") or [])})
    for color in colores_con_stock:
        if _menciona(texto, color):
            filtros["color"] = color
            break
    else:
        # Pidio un color que la tienda no tiene. Se manda igual: la busqueda va a
        # devolver cero y se contesta "no hay, pero tengo estos otros", que es lo
        # correcto. Si se descartara el color, se terminarian mostrando prendas
        # de cualquier tono como si fueran lo pedido.
        pedido = next((c for c in COLORES_CONOCIDOS if _menciona(texto, c)), None)
        if pedido:
            filtros["color"] = pedido
    for talla in ("XS", "XL", "S", "M", "L"):
        if f"talla {talla.lower()}" in texto:
            filtros["talla"] = talla
            break
    if not filtros:
        # Ultimo recurso: la palabra mas larga, que suele ser la que importa.
        palabras = [p for p in texto.replace("?", " ").replace("¿", " ").split() if len(p) > 4]
        if palabras:
            filtros["texto"] = max(palabras, key=len)
    return filtros


def _bs(valor) -> str:
    entero, _, decimales = f"{float(valor or 0):,.2f}".partition(".")
    return f"Bs {entero.replace(',', '.')},{decimales}"


def _redactar(herramienta: str, r: dict) -> str:
    """Arma una respuesta legible sin modelo de lenguaje."""
    if r.get("error"):
        return f"No pude consultar eso: {r['error']}"

    if herramienta in ("buscar_prendas", "recomendar_para_mi"):
        if not r.get("resultados"):
            aviso = r.get("aviso") or "No encontre nada con eso."
            colores = r.get("colores_con_stock")
            extra = f" Colores con stock hoy: {', '.join(colores)}." if colores else ""
            return aviso + extra
        lineas = [f"· {p['nombre']} — {_bs(p['precio'])}"
                  + (f" ({p['promocion']})" if p.get("promocion") else "")
                  for p in r["resultados"][:5]]
        encabezado = ("Te puedo recomendar:" if herramienta == "recomendar_para_mi"
                      else f"Encontre {r['cantidad']}:")
        cola = f"\nHay {r['hay_mas']} mas: afina la busqueda si queres." if r.get("hay_mas") else ""
        return encabezado + "\n" + "\n".join(lineas) + cola

    if herramienta == "promociones_vigentes":
        if not r.get("resultados"):
            return r.get("aviso", "Hoy no hay promociones.")
        return "Promociones de hoy:\n" + "\n".join(
            f"· {p['nombre']} ({p['descuento']}), hasta el {p['hasta']}" for p in r["resultados"])

    if herramienta == "mis_compras":
        if not r.get("resultados"):
            return "Todavia no tenes compras registradas."
        return "Tus ultimas compras:\n" + "\n".join(
            f"· {c['fecha']} — {_bs(c['total'])} (comprobante {c['comprobante']})"
            for c in r["resultados"])

    if herramienta == "mis_reservas":
        if not r.get("resultados"):
            return "No tenes reservas."
        return "Tus reservas:\n" + "\n".join(
            f"· #{v['id']} — {v['estado']} en {v['sucursal']}" for v in r["resultados"])

    if herramienta == "resumen_del_negocio":
        i = r["indicadores"]
        return (f"Del {r['periodo']['desde']} al {r['periodo']['hasta']}: "
                f"{_bs(i['total'])} en {i['ventas']} ventas ({i['unidades']} unidades). "
                f"Ticket promedio {_bs(i['ticket_promedio'])}, margen {i['margen_porcentaje']}%. "
                f"Contra el periodo anterior: {i['variacion_porcentaje']}%.")

    if herramienta == "stock_bajo":
        if not r.get("resultados"):
            return r.get("aviso", "Todo el stock esta por encima del minimo.")
        return (f"{r['cantidad']} variantes bajo el minimo:\n" + "\n".join(
            f"· {d['prenda']} {d['talla']}/{d['color']} en {d['sucursal']}: "
            f"quedan {d['disponible']}, faltan {d['faltan']}" for d in r["resultados"][:6]))

    if herramienta == "reporte_margen":
        res = r["resumen"]
        return (f"Ganancia promedio por prenda {_bs(res['ganancia_promedio_por_prenda'])}, "
                f"margen {res['margen_promedio_porcentaje']}%. "
                f"La que mas deja: {res['mayor_ganancia']}. La que menos: {res['menor_ganancia']}.")

    if herramienta == "reporte_inventario":
        t = r["totales"]
        return (f"Stock actual: {t.get('unidades')} unidades, valorizadas en "
                f"{_bs(t.get('valor_venta'))} a precio de venta.")

    if herramienta == "efectividad_recomendaciones":
        if not r.get("recomendaciones"):
            return r.get("detalle", "Todavia no hay recomendaciones para medir.")
        return (f"En {r['dias']} dias se recomendaron {r['recomendaciones']} prendas y se "
                f"compraron {r['compradas']}: {r['efectividad']}% de efectividad.")

    return json.dumps(r, ensure_ascii=False, default=str)[:600]


# ================================================================== consultas
def conversaciones(db: Session, usuario: Usuario) -> list[dict]:
    filas = (
        db.query(Conversacion)
        .filter(Conversacion.usuario_id == usuario.id, Conversacion.activa == True)  # noqa: E712
        .order_by(Conversacion.id.desc()).limit(20).all()
    )
    return [{"id": c.id, "titulo": c.titulo, "origen": c.origen,
             "creada": utc_iso(c.creada)} for c in filas]


def mensajes(db: Session, usuario: Usuario, conversacion_id: int) -> dict:
    conversacion = _conversacion(db, usuario, conversacion_id, None)
    filas = (
        db.query(MensajeChat)
        .filter(MensajeChat.conversacion_id == conversacion.id,
                MensajeChat.rol.in_(("usuario", "asistente")))
        .order_by(MensajeChat.id).all()
    )
    return {
        "conversacion_id": conversacion.id,
        "titulo": conversacion.titulo,
        "mensajes": [{"rol": m.rol, "texto": m.texto, "fecha": utc_iso(m.fecha)} for m in filas],
    }


def borrar(db: Session, usuario: Usuario, conversacion_id: int) -> dict:
    """Vacia el hilo. No se borra la fila: queda el rastro de que existio."""
    conversacion = _conversacion(db, usuario, conversacion_id, None)
    db.query(MensajeChat).filter(MensajeChat.conversacion_id == conversacion.id).delete()
    conversacion.activa = False
    db.commit()
    return {"conversacion_id": conversacion.id, "borrada": True}


def estado() -> dict:
    """Con que esta funcionando el asistente hoy."""
    return {
        "modelo": gemini.estado_del_servicio(),
        "recomendador": {"propio": True, "tipo": "contenido + popularidad",
                         "descripcion": "Perfil de gustos del cliente contra los atributos "
                                        "del catalogo. No depende de ningun servicio externo."},
    }
