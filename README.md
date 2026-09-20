# GangaClothes

Plataforma Inteligente de Comercio Electrónico para tienda de ropa con vestidores
virtuales vía Realidad Aumentada. Proyecto de **Sistemas de Información II** (UAGRM)
— Examen S2-2026, MSc. Ing. Angélica Garzón Cuéllar.

| Capa | Tecnología | Carpeta |
|---|---|---|
| Backend (API REST) | Python + **FastAPI** + SQLAlchemy | `backend/` |
| Frontend web | **Angular** | `web/` |
| App móvil | **Flutter + Dart** (cámara + ML Kit Pose para RA) | `mobile/` |
| Base de datos | **PostgreSQL** (Neon) | `backend/app/models/` |
| Pagos | **Stripe** (tarjeta) y **QR del BCP** (OpenBanking), ambos en modo prueba | `pagos/pasarelas/` |
| IA | Recomendador **propio** + asistente conversacional (Gemini, capa gratuita) | módulo `ia` |
| Modelado | UML 2.5 en draw.io | `docs/uml/` |

La equivalencia es:
> Model → `app/models/` (SQLAlchemy) · View → `app/modules/*/router.py` (endpoints)
> · Template → **no existe en el backend**: las "vistas" son Angular y Flutter.
> Los `schemas.py` (Pydantic) validan la entrada/salida como los forms/serializers.

---

## 1. Levantar el backend (2 minutos)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate     Linux/Mac:  source .venv/bin/activate
pip install -r requirements.txt
python seed.py                # crea tablas + datos de demostración (ver "Datos de demostración")
uvicorn app.main:app --reload
```

> **Ojo con `backend/.env`:** si existe y trae la `DATABASE_URL` de Neon, tanto el
> seed como la API trabajan contra **producción**. Para correr en local contra
> SQLite hay que forzar la variable en esa misma terminal:
>
> ```bash
> # Git Bash / Linux / Mac
> DATABASE_URL="sqlite:///./gangaclothes_dev.db" python seed.py
> DATABASE_URL="sqlite:///./gangaclothes_dev.db" uvicorn app.main:app --reload
> # PowerShell
> $env:DATABASE_URL = "sqlite:///./gangaclothes_dev.db"; python seed.py; uvicorn app.main:app --reload
> ```

Abrir **http://localhost:8000/docs** → ahí está TODO el contrato de la API,
agrupado por módulo y caso de uso. Ya no queda ningún módulo pendiente.

Usuarios de prueba del seed:

| Correo | Contraseña | Rol |
|---|---|---|
| admin@gangaclothes.com | Admin123 | administrador |
| encargado@gangaclothes.com | Encargado123 | encargado |
| cajero@gangaclothes.com | Cajero123 | cajero |
| sofia@gangaclothes.com | Cliente#2026 | cliente (tiene compras y reservas de historial) |
| diego@gangaclothes.com | Cliente#2026 | cliente |
| valeria@gangaclothes.com | Cliente#2026 | cliente |
| proveedor@gangaclothes.com | Proveedor123 | proveedor — Textiles Andinos SRL |
| oriente@gangaclothes.com | Proveedor123 | proveedor — Confecciones Oriente |

Cada rol ve solo lo suyo: el personal entra al panel (`/admin`), el cliente a la
tienda (`/catalogo`) y el proveedor a su portal (`/proveedor`). Las contraseñas
nuevas (registro, alta de usuarios, recuperación) exigen 8+ caracteres con
mayúscula, minúscula, número y símbolo; las del seed se cargan ya hasheadas.

Sin configurar nada usa **SQLite local** (`gangaclothes_dev.db`). Para usar
PostgreSQL real: copiar `.env.example` a `.env` y pegar la URL de Neon.

### Estructura del backend (patrón por módulos)

```
backend/app/
├── core/        config, conexión BD, seguridad JWT, dependencias (roles)
├── models/      las 37 tablas SQLAlchemy (el diagrama de clases tiene 28: ver
│                "Cambios al modelo de datos" en los Ciclos 3 y 5)
└── modules/     un módulo por paquete del análisis:
    ├── auth/            router + schemas + service   ← PATRÓN DE REFERENCIA
    ├── catalogos_base/  CRUD generado con la fábrica (comunes.py)
    ├── usuarios/ seguridad/ prendas/                 ← Iteración 1
    ├── inventario/ reservas/ ventas/ pagos/          ← Iteración 2
    ├── promociones/ reportes/ proveedores/           ← Iteración 3
    ├── pagos/pasarelas/  stripe_gw · qr_bcp          ← Iteración 4: una pasarela por archivo
    ├── ia/               recomendador · herramientas · gemini   ← Iteración 4 (CU28)
    └── envios/           tarifa · service · router               ← Iteración 5 (CU29)
```

Regla: los módulos con lógica de negocio (inventario, reservas, ventas, pagos)
se implementan con `router.py` + `service.py` copiando el patrón de `auth/`.
Los CRUD simples usan la fábrica `modules/comunes.py`.

---

## Ciclo 3 (Iteración 3): promociones, reportes y portal del proveedor

Tres módulos nuevos en `backend/app/modules/` con sus pantallas en `web/`, más
los cambios que hicieron falta en módulos que ya existían para que el descuento
y la oferta del proveedor se usen de verdad y no queden solo en pantalla.

### Casos de uso por módulo

| Módulo | Caso de uso | API | Pantalla web | Quién |
|---|---|---|---|---|
| `promociones/` | **CU18** Gestionar promociones | `/api/promociones` | `/admin/promociones` | administrador (`promociones:*`) |
| `reportes/` | **CU19** Reportes y dashboard | `/api/reportes/dashboard`, `/ventas`, `/inventario`, `/margen` | `/admin/dashboard`, `/admin/reportes` | quien tenga `reportes:ver` (administrador y encargado) |
| `proveedores/` | **CU9** Informar productos disponibles | `/api/oferta/perfil`, `/api/oferta/mia` | `/proveedor` | proveedor (`oferta:*`), siempre sobre **su** oferta |
| `proveedores/` + `inventario/` | **CU9 → CU10** la compra parte de la oferta | `/api/oferta`, `/api/oferta/{id}/prenda`, `/api/compras` | `/admin/oferta-proveedores`, `/admin/compras` | encargado y administrador |

Módulos de ciclos anteriores que cambiaron:

| Módulo | Qué cambió | CU afectados |
|---|---|---|
| `prendas/` | `GET /api/catalogo` y `/api/prendas/catalogo-interno` devuelven, además de `precio_venta`, `precio_final`, `descuento` y `promocion`. Campos **aditivos**: la app móvil sigue funcionando sin tocarla. | CU16, CU22 |
| `ventas/` | Carrito y caja aplican la promoción vigente; el comprobante detalla descuento y promoción por línea. | CU14, CU15, CU17 |
| `inventario/` | Cada línea de una compra parte de un producto de la oferta del proveedor. | CU10 |
| `usuarios/` | Una cuenta con rol `proveedor` se enlaza a **un** proveedor (`proveedor_id`). | CU3 |
| `core/permisos.py` | Módulo de permisos `OFERTA` y rol `proveedor`: 45 permisos en 13 módulos (el Ciclo 5 agrega `ENVIOS` y quedan **47 en 14**). | CU3 |

### Reglas de negocio que conviene saber

**Promociones (CU18)**
- Una promoción rige si está activa y hoy cae entre `fecha_inicio` y `fecha_fin`
  (ambas inclusive, hora de Bolivia). Tipo `porcentaje` (1 a 90) o `monto` fijo.
- `promociones/service.py` es la **única** fuente del precio con descuento: lo
  usan el catálogo, el carrito, la caja y el seed.
- Los descuentos **no se acumulan**. Si dos promociones vigentes alcanzan a la
  misma prenda se cobra la de mayor rebaja. El solapamiento se **advierte** (en
  el formulario antes de guardar, en la tarjeta de la promoción y en la
  bitácora con nivel ALERTA) pero no bloquea.
- Un descuento por monto no puede igualar ni superar el precio de la prenda.
  Medio centavo redondea hacia arriba (159,90 − 25% = 119,92).
- Una promoción que ya dio descuentos en alguna venta no se borra: se desactiva.

**Dinero en una venta.** `detalle_venta.precio_unitario` es el precio de lista,
`descuento` el descuento total de la línea y `subtotal` el neto. En `venta`:
`subtotal` = suma a precio de lista, `descuento` = suma de descuentos y
`total` = `subtotal − descuento`. Las ventas anteriores (descuento 0) siguen
siendo consistentes con esta lectura.

**Reportes (CU19)**
- Solo cuentan ventas **pagadas**, agrupadas en hora de Bolivia (UTC−4).
- Indicador del enunciado: **ganancia promedio por prenda** = promedio de
  (`precio_venta − costo`) de las prendas activas. Aparte se muestra la ganancia
  realizada por unidad vendida, con los descuentos ya restados.
- El costo es el actual de la prenda: el modelo no guarda costo histórico.
- Exportación: los tres reportes aceptan `?formato=csv` (lo arma el backend,
  con `;` y BOM para que Excel lo abra directo) y se imprimen o guardan como
  PDF desde el navegador. Los gráficos son SVG propio, sin librerías.

**Portal del proveedor (CU9) y compras (CU10)**
- El proveedor sale del token: nunca ve ni toca la oferta de otro (responde 404).
- Cada producto ofrecido lleva precio referencial, pedido mínimo, detalle libre
  (telas, colores, tallas) y una o más temporadas.
- Al crear una compra, cada línea es **producto del proveedor → variante destino
  → cantidad**; el precio referencial queda como sugerencia. Si el proveedor
  tiene oferta cargada, la API rechaza líneas que no partan de un producto suyo
  (o de uno que marcó sin disponibilidad). Si no tiene oferta, la compra se arma
  libremente y la pantalla lo avisa.
- El personal de la tienda define a qué prenda del catálogo corresponde cada
  producto (`/admin/oferta-proveedores`, o desde la misma compra). Con esa
  correspondencia el selector muestra primero las variantes de esa prenda; sin
  ella deja elegir cualquiera, advirtiéndolo. El proveedor no ve ese dato.
- Un producto del que ya partió alguna compra no se borra: queda sin disponibilidad.

### Cambios al modelo de datos respecto del diagrama de clases

El diagrama (`docs/uml/diagrama.png`) tiene **28 clases**; el código tiene **37
tablas** (36 al cerrar este ciclo, más `envio` en el Ciclo 5). La diferencia,
para actualizar el diagrama:

| Cambio | Tipo | Ciclo | Detalle |
|---|---|---|---|
| `producto_proveedor` | tabla nueva | 3 | `id`, `proveedor_id` FK→proveedor, `categoria_id` FK→categoria (0..1), `prenda_id` FK→prenda (0..1), `nombre`, `descripcion`, `precio_referencial`, `cantidad_minima`, `disponible`, `fecha_actualizacion`. Un proveedor tiene muchos productos. |
| `producto_proveedor_temporada` | tabla nueva (N a N) | 3 | `id`, `producto_id` FK→producto_proveedor, `temporada_id` FK→temporada; único (`producto_id`, `temporada_id`). |
| `producto_proveedor.prenda_id` | columna, admite nulo | 3 | Correspondencia con el catálogo: un producto corresponde a 0..1 prenda; una prenda puede tener varios productos. La define la tienda. |
| `detalle_compra.producto_proveedor_id` | columna nueva, admite nulo | 3 | De qué producto ofrecido partió la línea (0..1; nulo si el proveedor no tenía oferta). |
| `detalle_venta.promocion_id` | columna nueva, admite nulo | 3 | Promoción que originó el descuento de la línea (0..1). |
| `proveedor.usuario_id` | columna nueva, admite nulo, única | 3 | Cuenta con la que el proveedor entra a su portal (0..1 a 0..1 con `usuario`). La unicidad va en el modelo para bases nuevas; en una base migrada con `ALTER` la impone el servicio. |
| `permiso`, `rol_permiso`, `bitacora`, `recuperacion_contrasena` | tablas | 1 y 2 | Ya existían antes de este ciclo pero **no están en el diagrama**: permisos por rol, bitácora y recuperación de contraseña (`models/seguridad.py`). |
| `conversacion` | tabla nueva | 4 | Un hilo de chat con el asistente: `id`, `usuario_id` FK→usuario, `titulo`, `origen`, `creada`, `actualizada`, `activa`. Cuelga del **usuario** y no del cliente, porque el mismo asistente atiende al personal. |
| `mensaje_chat` | tabla nueva | 4 | Cada turno del hilo: `id`, `conversacion_id` FK→conversacion, `rol` (usuario/asistente/herramienta), `texto`, `herramienta`, `argumentos`, `fecha`. Las filas de rol `herramienta` no se muestran: quedan para poder auditar de dónde salió cada dato que el asistente dijo. |
| `evento_navegacion`, `recomendacion` | tablas | 4 | Estaban declaradas desde el Ciclo 1 pero sin uso; el Ciclo 4 las puso a trabajar (alimentan el recomendador y permiten medir si acierta). |

`promocion` y `promocion_prenda` ya estaban en el diagrama y no cambiaron.
No se usa Alembic: `create_all` crea las tablas nuevas y `core/migraciones.py`
agrega las columnas a las bases que ya existen (Neon y SQLite) con `ALTER TABLE`
idempotentes, al arrancar la API y al correr el seed.

### Variables de entorno y dependencias (Ciclo 3)

El Ciclo 3 no agregó ninguna dependencia: CSV y gráficos se resolvieron sin
librerías. Las del Ciclo 4 están más abajo, en su propia sección.

Una sola variable nueva, opcional (está en `backend/.env.example`):

| Variable | Para qué | Valor en Render |
|---|---|---|
| `IMAGENES_BASE_URL` | Las fotos del seed se guardan como ruta relativa (`/img/prendas/x.jpg`) y la web las resuelve sola. La **app móvil** necesita la URL completa: con esta variable el catálogo las devuelve absolutas. Vacía = relativas. | `https://ganga-clothes.vercel.app` |

Además, la API ahora expone la cabecera `Content-Disposition` por CORS (la web
lee de ahí el nombre del archivo al exportar un reporte); no requiere configurar nada.

### Datos de demostración (`python seed.py`)

`seed.py` crea permisos, roles y personal; `seed_demo.py` arma la tienda:

- **16 prendas** con foto (poleras, pantalones, vestidos, chamarras, camisas y
  faldas), precios y costos en bolivianos, marca y descripción.
- **3 sucursales** (Central y Norte en Santa Cruz, Cochabamba) con variantes
  talla-color y stock distinto en cada una: al filtrar el catálogo por sucursal
  cambia lo que se ve. Algunas variantes quedan en su mínimo para ver la alerta.
- **3 promociones vigentes** (vestidos −20%, jeans −Bs 40, poleras −15%) y una
  vencida (chamarras −25%), con fechas relativas al día en que se corre el seed.
- **84 ventas** de los últimos 45 días por caja, web y app (el Ciclo 5 suma 3
  más, las que se entregan a domicilio), con sus pagos,
  comprobantes y movimientos de stock; **10 reservas** en todos los estados; una
  compra ya recibida.
- **2 proveedores** con cuenta y oferta cargada (11 productos). Nueve ya tienen
  correspondencia con una prenda; *Jogger tela fluida* y *Parka impermeable con
  capucha* quedan sin ella a propósito, para mostrar la advertencia en la compra.

Es idempotente: se puede correr varias veces y encima de una base con datos
(busca por nombre, solo abre el stock que falta y genera el historial una única
vez). Las cantidades salen de un generador con semilla fija. Las fotos están en
`web/public/img/prendas/` y vienen de Unsplash (ver `CREDITOS.md` ahí mismo).

---

---

## Ciclo 4 (Iteración 4): pasarelas de pago, comprobante e IA

Lo que exige el enunciado en esta iteración: cobrar de verdad por una pasarela,
emitir el comprobante imprimible, y que el sistema tenga inteligencia artificial
útil tanto para el cliente como para quien administra la tienda.

| Módulo | Caso de uso | API | Pantalla | Quién |
|---|---|---|---|---|
| `pagos/pasarelas/` | **CU17** Pago en línea por pasarela | `/api/pagos`, `/api/pagos/metodos`, `/api/pagos/qr` | carrito de la tienda | cliente (sobre su propia compra) |
| `pagos/` | **CU15** Cobro en caja | `/api/pagos` | `/admin/caja` | cajero y administrador (`pagos:crear`) |
| `ventas/comprobante_pdf.py` | **CU15** Comprobante imprimible | `/api/ventas/{id}/comprobante.pdf` | caja y confirmación de compra | quien pueda ver esa venta |
| `ia/recomendador.py` | **CU28** Recomendaciones | `/api/ia/recomendaciones`, `/api/ia/eventos` | catálogo y asistente | cliente |
| `ia/` (asistente) | **CU28** Asistente conversacional | `/api/ia/chat` | burbuja flotante, en toda la web | cliente y personal, con herramientas distintas |

Módulos que cambiaron para esto:

| Módulo | Qué cambió |
|---|---|
| `pagos/` | El cobro se separó del proveedor: `service.py` decide qué pasa con la venta y `pasarelas/` habla con cada proveedor. Sigue siendo el **único** lugar que descuenta inventario. `pasarela` se acepta como sinónimo de `tarjeta`, así que la app Flutter no necesita cambios. |
| `ventas/` | El comprobante agrega ciudad, teléfono de la sucursal, la forma de pago y la fecha escrita en hora de Bolivia; y se puede pedir en PDF. |
| `ia/` | Dejó de ser un stub: recomendador propio, asistente con herramientas y memoria de conversación. |
| `models/ia.py` | Dos tablas nuevas para el hilo del chat: `conversacion` y `mensaje_chat`. |

### Métodos de pago (CU15 · CU17)

La tienda en línea cobra por **dos pasarelas reales** y la caja registra el cobro
de mostrador. Qué ofrece cada pantalla lo decide el backend y se consulta en
`GET /api/pagos/metodos?canal=web|movil|caja`: si mañana falta una clave, ese
método deja de aparecer solo, sin tocar la web.

| Canal | Métodos | Quién cobra |
|---|---|---|
| web y móvil | **tarjeta** (Stripe) · **QR** (Banco de Crédito de Bolivia) | el propio cliente |
| caja | efectivo · tarjeta · QR | el cajero, con permiso `pagos:crear` |

Cada pasarela vive en su archivo y no sabe nada del negocio:

```
backend/app/modules/pagos/
├── service.py              decide qué pasa con la venta (único lugar que toca inventario)
└── pasarelas/
    ├── cliente_http.py     HTTPS con autenticación básica y certificado de cliente
    ├── stripe_gw.py        tarjeta por Stripe
    └── qr_bcp.py           QR del BCP: generar y consultar
```

**Tarjeta (Stripe, modo prueba).** El número **no viaja a Stripe**: se manda uno
de sus *payment methods* de prueba, que es lo que la cuenta permite sin habilitar
tarjetas en crudo. El número que escribe el cliente solo elige cuál —
`4242 4242 4242 4242` aprueba y `4000 0000 0000 0002` lo rechaza el emisor. El
cobro se resuelve en la misma llamada.

Cualquier otro número **se rechaza**, con dos filtros: el formulario valida el
dígito de Luhn (lo mismo que hace cualquier pasarela antes de llamar al banco) y
el backend no cobra nada que no sea una tarjeta de prueba de Stripe. Dar por
buena una cifra cualquiera de 16 dígitos haría creer que se cobró cuando no se
cobró nada.

**QR (BCP OpenBanking).** El cobro ocurre fuera del sistema: se genera el QR, el
cliente lo escanea con su banca móvil y la pantalla pregunta al banco cada pocos
segundos cómo quedó (`C` en cola, `P` pagado, `V` vencido, `A` anulado). Son tres
endpoints, los mismos para la web y para la app:

```
POST /api/pagos/qr            genera el QR y deja el pago en pendiente
GET  /api/pagos/qr/{qr_id}    consulta al banco; si se pagó, cierra la venta
POST /api/pagos/qr/simular    solo con BCP_MODO=simulado, fuerza el desenlace
```

> **Por qué hay un simulador.** El sandbox del BCP exige TLS mutuo: además de
> usuario, contraseña, `appUserId`, `publicToken` y `businessCode`, hay que
> presentar el **certificado `.pfx`** que entrega el banco. Sin él, el host
> responde `403` antes de mirar las credenciales. Con `BCP_MODO=simulado` el QR
> se genera localmente (es un QR real, escaneable) y el flujo completo se puede
> demostrar. Cuando llegue el certificado: `BCP_MODO=sandbox` y `BCP_CERT_PFX`
> con su ruta — ninguna otra línea cambia.
>
> El simulador hace además de pagador: a los `BCP_SIMULADOR_SEGUNDOS` (8 por
> defecto) da el QR por cobrado, como si alguien lo hubiera escaneado. Así la
> compra con QR se completa sola y **la pantalla del cliente no tiene ningún
> botón de prueba**. Con `BCP_SIMULADOR_SEGUNDOS=0` el QR espera hasta vencer,
> que es como se demuestra el desenlace rechazado; forzarlo a mano sigue siendo
> posible desde `POST /api/pagos/qr/simular`, que no usa ninguna pantalla.

**Estado de la conexión con el banco.** El certificado ya está y la conexión con
el sandbox **funciona**: TLS mutuo completo y el banco autenticándonos y
respondiendo su API. Se comprueba corriendo `probar-bcp-sandbox.py` (está con el resto de los
scripts de prueba, fuera del repositorio) desde `backend/` con `BCP_MODO=sandbox`:
verifica el certificado, el handshake y la respuesta del banco.

Dos cosas que costaron encontrar y que no están en el manual:

- **El banco no responde por TLS 1.3.** Completa el handshake y después cierra la
  conexión sin contestar. Hay que limitar la versión a TLS 1.2 (es lo mismo que
  su manual pide configurar a mano en Postman). Se hace solo para el BCP:
  Stripe sigue con TLS moderno.
- **El `.pfx` viene con contraseña**, pero el mismo paquete trae el par PEM
  (`.crt` + `.key`) sin cifrar, que OpenSSL lee directo. Se usa ese; el `.pfx`
  queda soportado igual por si en producción entregan solo ese.

Lo único que falta para cobrar de verdad por QR es la **especificación de
generación**: el PDF que tenemos es el de *consulta de estado*, y el endpoint
para crear el QR no figura en ningún documento ni responde en las rutas
esperables. Hasta que el banco lo entregue, la tienda funciona con
`BCP_MODO=simulado`.

**Los dos desenlaces, siempre.** Si la pasarela aprueba, se emite comprobante y
se descuenta el inventario, todo en la misma transacción. Si rechaza, la venta
**vuelve al carrito** intacta y el inventario no se toca; el pago fallido igual
queda registrado y en la bitácora con nivel `ERROR`.

`pasarela` se sigue aceptando como sinónimo de `tarjeta`: la app Flutter no
necesita cambios.

### IA: recomendador y asistente (CU28)

Dos piezas que se complementan, y conviene no confundirlas:

| | Quién decide | De qué depende |
|---|---|---|
| **Recomendador** | nuestro, en `ia/recomendador.py` | de nada externo |
| **Asistente** | Gemini (capa gratuita) | de una clave; si falta, sigue andando |

**El recomendador es el que elige las prendas.** Arma un perfil de gustos del
cliente con lo que compró (peso 3), reservó (2) y miró (1), y puntúa cada prenda
del catálogo por categoría, color, marca, colección, cercanía de precio y
popularidad, con bonus si está en promoción o si hay stock en su talla habitual.
Cada sugerencia sale con su **motivo** ("porque solés comprar vestidos"), no con
un número suelto: en la defensa hay que poder explicar por qué apareció cada
prenda. Sin historial arranca con lo más vendido y lo que está rebajado.

**El asistente solo conversa.** No busca ni calcula: pide. Cada consulta suya es
una función de `ia/herramientas.py` que va a nuestra base, y el modelo únicamente
recibe el resultado. De ahí salen las dos propiedades que importan:

- **No puede inventar.** Si una prenda no vino de una herramienta, no la tiene.
  Pedile "una polera violeta" y responde que no hay, y ofrece los colores que sí
  existen — en vez de mostrar poleras de otro color como si fueran lo pedido.
- **Siempre está al día.** Se consulta en vivo, sin copia guardada: una prenda
  publicada hace un minuto ya se puede recomendar, y una que se quedó sin stock
  desaparece sola.

Cada rol ve su propia caja de herramientas, según el permiso `reportes:ver` que
ya existía:

| Cliente | Personal |
|---|---|
| `buscar_prendas` · `recomendar_para_mi` · `ver_prenda` · `promociones_vigentes` · `mis_compras` · `mis_reservas` | `resumen_del_negocio` · `reporte_ventas` · `reporte_margen` · `reporte_inventario` · `stock_bajo` · `efectividad_recomendaciones` |

Las del personal son envoltorios de los reportes del CU19: el asistente responde
"¿cómo vienen las ventas?" con las mismas cifras que el panel.

```
GET  /api/ia/estado              con qué motor está funcionando hoy
GET  /api/ia/recomendaciones     el carrusel "para vos", sin chat de por medio
POST /api/ia/eventos             registra qué prenda miró el cliente
POST /api/ia/chat                conversar (memoria por conversación)
GET  /api/ia/conversaciones      los hilos, y /{id} su historial
```

Las recomendaciones salen **con la misma forma que `GET /api/catalogo`** más
`motivo` y `puntaje`, para que la web y la app móvil reusen el modelo de prenda
que ya tienen.

> **Si falta la clave, el asistente no se cae.** Sin `GEMINI_API` responde en
> modo *sin modelo*: reconoce la intención por palabras, usa las mismas
> herramientas y contesta con los datos en crudo. Más seco, pero funciona — y
> evita que una cuota agotada arruine una demostración.

### Comprobante en PDF (CU15)

```
GET /api/ventas/{id}/comprobante        datos en JSON
GET /api/ventas/{id}/comprobante.pdf    el PDF (?descargar=true para bajarlo)
```

El mismo documento para la venta en caja y para la compra web: datos de la
tienda y la sucursal, número, fecha **en hora de Bolivia**, cliente, detalle con
talla y color, descuentos por línea con su promoción, subtotal, total y forma de
pago. Lo dibuja `ventas/comprobante_pdf.py` con ReportLab. En pantalla hay
**Imprimir comprobante** (abre el visor del navegador) y **Descargar PDF**, tanto
en la caja como en la confirmación de compra del cliente.

### Variables de entorno y dependencias (Ciclo 4)

Tres librerías nuevas en `backend/requirements.txt`, todas con una razón concreta:

| Librería | Para qué |
|---|---|
| `reportlab` | Dibujar el comprobante en PDF |
| `qrcode` | El QR del simulador, que es un QR real y escaneable |
| `cryptography` | Leer el certificado `.pfx` del banco si se usa esa forma |

En el frontend no se agregó ninguna: el chat, el QR y la impresión se resolvieron
con lo que ya había.

Las variables están todas en `backend/.env.example`. **Ninguna clave va al
código**, y en Render se cargan en el panel *Environment*:

| Variable | Para qué | Si falta |
|---|---|---|
| `STRIPE_SECRET_KEY` · `STRIPE_PUBLIC_KEY` | Cobrar con tarjeta (modo prueba) | El método deja de ofrecerse solo |
| `GEMINI_API` | El asistente conversacional | El asistente responde igual, en modo *sin modelo* |
| `BCP_MODO` | `simulado`, `sandbox` o `live` | `simulado` |
| `BCP_USUARIO` · `BCP_PASSWORD` · `BCP_APP_USER_ID` · `BCP_PUBLIC_TOKEN` · `BCP_BUSINESS_CODE` · `BCP_SERVICE_CODE` | Credenciales del banco | Solo hacen falta fuera de `simulado` |
| `BCP_CERT_PEM` · `BCP_CERT_KEY` | Certificado de cliente del banco, en PEM | Idem; sin él el banco responde 403 |
| `BCP_CERT_PFX` · `BCP_CERT_PASSWORD` | Alternativa al par PEM | — |
| `BCP_QR_MINUTOS` · `BCP_SIMULADOR_SEGUNDOS` | Cuánto vive un QR y a los cuántos segundos lo paga el simulador | 15 y 8 |
| `GEMINI_MODELOS` · `IA_MAX_PASOS` · `IA_MEMORIA_MENSAJES` | Ajustes del asistente | Valores razonables por defecto |

> **Los certificados del banco no se versionan.** Viven en `GangaClothes/certificados/`
> y `.gitignore` tapa esa carpeta y además `*.pfx`, `*.p12`, `*.pem`, `*.crt`,
> `*.key` y `*.cer`, por si alguien los deja en otro lado.

**Una decisión de diseño que se repite en los tres módulos:** cada servicio
externo se declara *disponible o no* según sus variables de entorno, y la
pantalla pregunta antes de ofrecerlo (`GET /api/pagos/metodos`, `GET /api/ia/estado`).
Si mañana falta una clave, el método o el asistente se degradan solos en vez de
fallar delante del usuario.

---

## Ciclo 5 (Iteración 5): delivery de las compras digitales

El último módulo: la compra en línea ahora se puede **retirar en sucursal** o
pedir **a domicilio**. El delivery es **simulado** —no se integra ningún
servicio de reparto— pero todo lo demás es real: el costo se calcula con una
tarifa explicable, el cliente marca su ubicación en un mapa y ve el desglose
antes de pagar, y el encargado despacha el pedido desde el panel.

| Módulo | Caso de uso | API | Pantalla web | Quién |
|---|---|---|---|---|
| `envios/` | **CU29** Pedir entrega a domicilio | `/api/envios/cotizar`, `/api/envios` | carrito de la tienda | cliente (sobre su propia compra) |
| `envios/` | **CU29** Seguir mi pedido | `/api/envios/mios` | `/mis-envios` | cliente |
| `envios/` | **CU29** Despachar los envíos | `/api/envios`, `/{id}/asignar`, `/en-camino`, `/entregar`, `/cancelar` | `/admin/envios` | encargado y administrador (`envios:*`) |

Módulos de ciclos anteriores que cambiaron:

| Módulo | Qué cambió |
|---|---|
| `ventas/` | La venta guarda **cómo se entrega** (`tipo_entrega`) y **cuánto cuesta el envío** (`costo_envio`), que ahora es parte de `total`. El carrito recotiza el envío en cada cambio. Campos **aditivos**: la app móvil sigue funcionando sin tocarla. |
| `pagos/` | Ninguno. Cobra `venta.total`, que ya trae el envío adentro; el inventario se sigue descontando al pagarse, no al entregarse. |
| `reportes/` | El costo del envío se **descuenta** del total al medir ventas: es servicio de reparto, no mercadería, y si no el margen saldría inflado. |
| `ventas/comprobante_pdf.py` | El comprobante muestra el envío como línea aparte y un bloque con la dirección de entrega. En retiro en sucursal queda exactamente igual que antes. |
| `catalogos_base/` | La sucursal tiene `latitud` y `longitud`, editables desde `/admin/sucursales`. Sin coordenadas, esa sucursal solo ofrece retiro. |
| `core/permisos.py` | Módulo de permisos `ENVIOS`: **47 permisos en 14 módulos**. |

### El cálculo del costo (Parte I del informe)

Vive entero en `backend/app/modules/envios/tarifa.py`, que es la **única** fuente
del precio de un envío: lo usan la cotización del checkout, la creación del
envío y el seed. Son cuatro reglas y ninguna sorpresa:

| # | Regla | Valor |
|---|---|---|
| 1 | Costo base fijo, por salir a repartir | Bs 12,00 |
| 2 | Costo por kilómetro hasta el destino | Bs 3,50 × km |
| 3 | Recargo por urgencia (entrega express) | +45% sobre (1 + 2) |
| 4 | Envío gratis a partir de cierto monto de compra | desde Bs 500,00 |

Y un límite: **fuera de 25 km** alrededor de la sucursal no se reparte. La
pantalla lo avisa con el texto ya redactado en vez de cobrar un envío imposible.

La distancia sale de la **fórmula de Haversine** entre las coordenadas de la
sucursal y las del destino:

```
a = sin²(Δlat/2) + cos(lat₁) · cos(lat₂) · sin²(Δlon/2)
d = 2 · R · asin(√a)          con R = 6371,0088 km
```

Es la distancia en línea recta sobre la superficie de la Tierra, **no** el
recorrido por calle: para eso haría falta un servicio de ruteo, y el delivery de
este proyecto es simulado. Por eso el tiempo estimado usa una velocidad
conservadora (18 km/h, moto en ciudad con tráfico), que ya descuenta que el
camino real es más largo que la recta. El express además se prepara en 15
minutos en vez de 45.

**El desglose se muestra siempre, no solo el total.** `POST /api/envios/cotizar`
devuelve un renglón por concepto (base, distancia, recargo y, si corresponde, la
bonificación por envío gratis en negativo), y la pantalla los pinta uno por uno.
Los importes suman exactamente el costo cobrado: eso lo verifica una prueba.

### Reglas de negocio que conviene saber

- **Una venta tiene a lo sumo un envío**, y solo si el cliente eligió delivery.
  Con retiro en sucursal no hay fila en `envio`.
- **El costo entra en el total**: `total = subtotal − descuento + costo_envio`.
  La pasarela cobra ese total, así que pagar solo la mercadería se rechaza.
- **El precio lo calcula el servidor, siempre.** La pantalla lo muestra, no lo
  propone: si viniera del navegador, cualquiera pediría envío gratis.
- **El envío se arma antes de pagar** (con la venta en carrito o pendiente) y se
  recotiza solo mientras la compra no esté pagada: si el carrito cruza el mínimo
  de envío gratis, el cliente lo ve enseguida. Un carrito vacío no paga envío.
- **Si el cliente cambia la sucursal de despacho** por una que no llega hasta su
  dirección, la compra vuelve sola a retiro en sucursal en vez de trabarle el
  carrito. La cobertura se valida al elegir la dirección, que es donde el
  mensaje sirve.
- **Un envío es un pedido recién cuando la compra está pagada.** Un delivery a
  medio armar en un carrito no aparece ni en «mis pedidos» ni en el panel de la
  sucursal.
- **El inventario se descuenta al pagarse**, como cualquier otra venta. Entregar
  es mover un paquete que ya se cobró.
- **Cancelar un envío no anula la venta**: la compra ya se cobró y el stock ya
  salió. Lo que queda es coordinar con el cliente el retiro en sucursal o la
  devolución, que es el CU de anulación de ventas y no entra en este ciclo. La
  pantalla del encargado lo dice con todas las letras antes de confirmar.

Estados y quién los mueve:

```
pendiente ──asignar──▶ asignado ──en-camino──▶ en_camino ──entregar──▶ entregado
     │                     │                        │
     └─────────────────────┴────────────────────────┴──▶ cancelado
```

El cliente solo puede deshacer su envío **antes de pagar** (vuelve a retiro en
sucursal). Una vez cobrada la compra, el estado lo mueve el encargado.

### El mapa: Leaflet + OpenStreetMap

```
web/src/app/shared/mapa/mapa.ts        el componente, con tiles de OpenStreetMap
web/src/app/shared/entrega/envio.ts    tipo del envío, línea de tiempo y puntos del mapa
```

**OpenStreetMap es gratis y no pide clave ni tarjeta**, a diferencia de Google
Maps o Mapbox. A cambio exige mostrar su atribución, que va en el pie del mapa.
El mismo componente sirve a las tres pantallas: en el checkout es seleccionable
(el cliente toca el mapa para marcar su ubicación), en el seguimiento une origen
y destino con una línea, y en el panel del encargado marca todos los destinos
pendientes de la sucursal.

Los marcadores son `divIcon` —HTML y CSS— y no las imágenes que trae Leaflet:
así no hay que copiar PNG al build ni pelear con las rutas que el empaquetador
les cambia, y además quedan con los colores de la tienda.

Para escribir la dirección **no se usa ningún servicio de geocodificación**: el
cliente escribe la calle como texto libre y marca el punto exacto en el mapa (o
usa el botón «usar mi ubicación actual», que es la API del navegador). Un
geocodificador sería un servicio externo más, y el enunciado pide que el
delivery no integre ninguno.

### Cambios al modelo de datos respecto del diagrama de clases

| Cambio | Tipo | Detalle |
|---|---|---|
| `envio` | **tabla nueva** | `id`, `venta_id` FK→venta (**única**: una venta tiene 0..1 envío), `direccion`, `latitud`, `longitud`, `referencia`, `telefono_contacto`, `distancia_km`, `costo_envio`, `express`, `estado`, `repartidor`, `motivo_cancelacion`, `fecha_creacion`, `fecha_asignacion`, `fecha_salida`, `fecha_estimada`, `fecha_entrega`. |
| `venta.tipo_entrega` | columna nueva, admite nulo | `sucursal` (retiro) o `delivery`. Nulo se lee como `sucursal`, que es lo que eran todas las ventas anteriores. En caja siempre es `sucursal`. |
| `venta.costo_envio` | columna nueva, admite nulo | Lo que se cobra por el reparto; 0 en retiro en sucursal. Es parte de `venta.total`. |
| `sucursal.latitud`, `sucursal.longitud` | columnas nuevas, admiten nulo | El punto del mapa desde el que sale el delivery. Sin ellas la sucursal funciona igual, pero solo ofrece retiro. |

Detalles para dibujar el diagrama:

- `envio` — `venta` es **1 a 0..1**: el envío no existe sin su venta, y una
  venta puede no tener envío. De qué sucursal sale **no se repite** en `envio`:
  es la de la venta (`venta.sucursal_id`), que es la que tiene el stock y las
  coordenadas de origen.
- Las coordenadas van en `Float` y no en `Numeric` porque no son dinero: se usan
  para medir distancias, no para sumar importes. La distancia y el costo sí son
  `Numeric`, porque el costo se cobra y tiene que cuadrar al centavo.
- `distancia_km` y `costo_envio` quedan **congelados** al confirmar la compra:
  si mañana cambia la tarifa, ese envío sigue valiendo lo que el cliente aceptó.
- El repartidor es **un nombre**, no una tabla: el reparto es simulado y no hay
  un caso de uso que administre repartidores. Si más adelante lo hubiera, sería
  una tabla `repartidor` y `envio.repartidor_id`.

Como en los ciclos anteriores, no se usa Alembic: `create_all` crea la tabla
nueva y `core/migraciones.py` agrega las columnas a las bases que ya existen
(Neon y SQLite) con `ALTER TABLE` idempotentes.

### La app móvil (Flutter) — contrato listo

El backend queda terminado y documentado para que Integrante 2 arme las
pantallas sin esperar nada:

> **`docs/delivery-api.md`** — el contrato completo: cada endpoint con su
> petición y su respuesta, el flujo de la compra paso a paso, el ejemplo de
> `flutter_map` y las coordenadas de Santa Cruz para probar.

Resumen de lo que consume la app:

| Endpoint | Para qué |
|---|---|
| `GET /api/envios/tarifa` | las reglas del cobro (público, sin sesión) |
| `POST /api/envios/cotizar` | distancia, costo desglosado y tiempo; **no crea nada** |
| `POST /api/envios` | pedir la entrega a domicilio de una compra |
| `DELETE /api/envios/{id}` | volver a retiro en sucursal, antes de pagar |
| `GET /api/envios/mios` | seguimiento de mis pedidos |
| `GET /api/envios/{id}` | un pedido (el cliente, solo los suyos) |

El paquete del mapa es **[`flutter_map`](https://pub.dev/packages/flutter_map)**,
que es Leaflet para Flutter y consume los mismos tiles de OpenStreetMap que la
web (gratis, sin clave ni tarjeta):

```yaml
dependencies:
  flutter_map: ^7.0.2
  latlong2: ^0.9.1          # el tipo LatLng que usa flutter_map
  geolocator: ^13.0.1       # opcional: botón "usar mi ubicación"
```

La app no replica ninguna cuenta del costo: muestra el `desglose` que devuelve
`cotizar` y paga `venta.total`. Si no implementa delivery, `tipo_entrega` queda
en `sucursal`, `costo_envio` en 0 y **nada cambia** respecto de lo que ya tiene.

### Variables de entorno y dependencias (Ciclo 5)

**Ninguna variable nueva y ninguna dependencia nueva en el backend.** La tarifa
son constantes documentadas en `tarifa.py` y Haversine es una fórmula, no una
librería. En el frontend, una sola dependencia:

| Librería | Para qué |
|---|---|
| `leaflet` (y `@types/leaflet`) | el mapa, con tiles de OpenStreetMap |

Su hoja de estilos se carga desde `angular.json` (`node_modules/leaflet/dist/leaflet.css`)
y la librería se declara en `allowedCommonJsDependencies` porque se publica en
CommonJS: sin eso el build avisa en cada compilación.

### Datos de demostración (Ciclo 5)

`seed_demo.py` agrega:

- **coordenadas reales** para las tres sucursales, tomadas de OpenStreetMap:
  Central en el casco viejo de Santa Cruz, Norte sobre la Av. Banzer y 4to
  anillo, y Cochabamba en el Prado;
- **3 envíos a domicilio** de compras pagadas, en estados distintos —uno
  `entregado` en Equipetrol, uno `en_camino` y **express** hacia el 6to anillo, y
  uno `pendiente` en el Plan 3000 a 9 km—, cada uno de una clienta distinta y con
  las horas de cada paso cargadas, para que la línea de tiempo del seguimiento se
  vea completa desde el primer minuto de la demostración.

Los envíos llevan **su propia marca de idempotencia** (si ya hay alguno, no se
cargan), así que aparecen también al correr el seed sobre una base que ya traía
el historial de ventas de otro ciclo —la de producción, sin ir más lejos.

---

## 2. Levantar el frontend web (Angular) — Ariany

```bash
cd web
npm install
npm start            # http://localhost:4200, contra la API en http://localhost:8000/api
```

La URL de la API sale de `src/environments/api-url.ts`; la compilación de
producción la reemplaza por `api-url.prod.ts` (la de Render). En local el login
muestra atajos con las cuentas del seed (`environments/cuentas-demo.ts`); en
producción ese archivo se reemplaza por una lista vacía.

```
web/src/app/
├── core/        sesión y JWT, guards por rol y por permiso, URL de la API
├── shared/      CRUD genérico, selectores, avisos, formato, gráficos (SVG propio)
└── features/
    ├── auth/        login, registro, recuperar contraseña
    ├── catalogo/  tienda/           catálogo público, carrito, mis compras,
    │                                mis reservas y mis pedidos a domicilio (CU29)
    ├── admin/                       panel: usuarios, roles, bitácora, catálogos base,
    │                                prendas y promociones (CU18)
    ├── inventario/                  inventario, movimientos, compras y
    │                                oferta de proveedores (CU9 -> CU10)
    ├── reservas/  caja/             reservas de la sucursal y venta en caja
    ├── reportes/                    dashboard y reportes (CU19)
    ├── envios/                      envíos a domicilio de la sucursal (CU29)
    └── proveedor/                   portal del proveedor (CU9)
```

El menú del panel (`features/admin/menu.ts`) filtra por rol y, donde el ítem lo
declara, también por permiso: lo que se quita en «Roles y permisos» desaparece
del menú, de la ruta (`permisoGuard`) y de la API a la vez.

---

## 3. Crear la app móvil (Flutter) — Integrante 2

```bash
flutter create mobile --org com.gangaclothes --platforms android
cd mobile && flutter run
```

Dependencias a agregar en `pubspec.yaml`:

```yaml
dependencies:
  dio: ^5.4.0                          # HTTP
  shared_preferences: ^2.2.0           # guardar token
  camera: ^0.11.0                      # probador RA (CU24)
  google_mlkit_pose_detection: ^0.14.0 # detección del cuerpo (CU24)
  image_picker: ^1.1.0                 # foto del rostro para el avatar (CU23)
```

Estructura acordada: `lib/core/` (api, sesión) y
`lib/features/{catalogo,probador_ar,avatar,reservas,carrito,perfil}/`
cada una con `data/ domain/ presentation/`.

`lib/core/api.dart` (mínimo para arrancar):

```dart
import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

// Emulador Android: 10.0.2.2 apunta al localhost de tu PC.
const apiUrl = 'http://10.0.2.2:8000/api'; // en producción: URL de Render

final dio = Dio(BaseOptions(baseUrl: apiUrl))
  ..interceptors.add(InterceptorsWrapper(onRequest: (o, h) async {
    final token = (await SharedPreferences.getInstance()).getString('token');
    if (token != null) o.headers['Authorization'] = 'Bearer $token';
    h.next(o);
  }));
```

---

## 4. Flujo de trabajo para NO pisarnos

**Propiedad de carpetas** (cada uno toca solo lo suyo; lo compartido, por acuerdo):

| Carpeta | Dueño |
|---|---|
| `backend/**` | Integrante 1 |
| `web/**` (toda la web) | Ariany |
| `mobile/**` | Integrante 2 |
| `docs/**`, `README.md`, `app/models/**` | Ambos, avisando antes |

**Reglas Git:**

1. Nunca commitear directo a `main`.
2. Rama por tarea: `feature/backend-inventario`, `feature/app-probador-ar`, etc.
3. `git pull origin main` antes de empezar el día.
4. Terminaste → push de tu rama → Pull Request → el otro revisa y aprueba.
5. El **contrato** entre ambos es `/docs` (OpenAPI): Integrante 2 desarrolla
   pantallas contra ese contrato sin esperar el código del backend. Para el
   delivery (CU29), además, está `docs/delivery-api.md` con el flujo completo y
   el ejemplo de `flutter_map`.

```bash
git clone https://github.com/ary10220/GangaClothes.git
cd GangaClothes
git checkout -b feature/mi-tarea
# ... trabajar ...
git add . && git commit -m "feat: descripcion"
git push -u origin feature/mi-tarea   # → abrir PR en GitHub
```

---

## 5. Despliegue en la nube (obligatorio, no localhost)

1. **Neon** (BD): crear proyecto gratis → copiar la connection string → ponerla
   como `DATABASE_URL` en Render y en tu `.env` local para probar contra la BD real.
2. **Render** (API): New → Web Service → conectar este repo →
   Root Directory `backend` · Build `pip install -r requirements.txt` ·
   Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT` ·
   Variables: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS=*` y, para que la app
   móvil vea las fotos del catálogo, `IMAGENES_BASE_URL` (ver Ciclo 3).
   Luego correr el seed una vez desde la Shell de Render: `python seed.py`.
3. **Vercel** (web): importar el repo → Root Directory `web` → framework Angular.
4. **APK**: `flutter build apk --release` → subir a un Release de GitHub → ese
   enlace + QR van en el documento.

---

## 6. Tareas Semana 1 (Iteración 1 → Presentación #1, sáb 05/09)

> Ver `docs/Reparto.md` para la lista completa de diagramas y pantallas
> de las 3 iteraciones con responsable asignado.

**Ariany** ✅ backend Iteración 1 terminado — le queda:
- [ ] Subir esta base al repo y desplegar Neon + Render (probar `/docs` en línea).
- [ ] Pantallas Angular: login, dashboard admin, CRUD catálogos base, CRUD
      ciudades/sucursales, CRUD prendas+variantes, catálogo público del cliente.
- [ ] Diagramas: D4 CU Iteración 1, D7 CU General del Sistema, D12 Comunicación It.1.

**Compañero**
- [ ] `flutter create mobile` + login/registro consumiendo `/api/auth`.
- [ ] Catálogo móvil con filtros consumiendo `/api/catalogo`.
- [ ] Detalle de prenda con disponibilidad por sucursal.
- [ ] Prueba técnica del probador RA (cámara + ML Kit).
- [ ] Diagramas: D1-D3 Actividad (3 flujos), D5 CU It.2, D9 Paquetes,
      D15 Clases análisis It.1, D19 Despliegue.

**Ambos:** completar carátula del informe, generar el QR del repo y pegar
capturas del prototipo en el documento.
