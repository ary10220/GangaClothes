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
| Pagos | Stripe en **modo prueba** | módulo `pagos` |
| IA | Recomendador propio vía API | módulo `ia` |
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

Abrir **http://localhost:8000/docs** → ahí está TODO el contrato de la API
(lo implementado y lo pendiente con su responsable e iteración).

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
├── models/      las 34 tablas SQLAlchemy (el diagrama de clases tiene 28: ver
│                "Cambios al modelo de datos" en la sección del Ciclo 3)
└── modules/     un módulo por paquete del análisis:
    ├── auth/            router + schemas + service   ← PATRÓN DE REFERENCIA
    ├── catalogos_base/  CRUD generado con la fábrica (comunes.py)
    ├── usuarios/ seguridad/ prendas/                 ← Iteración 1
    ├── inventario/ reservas/ ventas/ pagos/          ← Iteración 2
    ├── promociones/ reportes/ proveedores/           ← Iteración 3 (ver abajo)
    └── ia/                                           ← stub con plan y responsable (CU28)
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
| `core/permisos.py` | Módulo de permisos `OFERTA` y rol `proveedor`: 45 permisos en 13 módulos. | CU3 |

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

El diagrama (`docs/uml/diagrama.png`) tiene **28 clases**; el código tiene **34
tablas**. La diferencia, para actualizar el diagrama:

| Cambio | Tipo | Ciclo | Detalle |
|---|---|---|---|
| `producto_proveedor` | tabla nueva | 3 | `id`, `proveedor_id` FK→proveedor, `categoria_id` FK→categoria (0..1), `prenda_id` FK→prenda (0..1), `nombre`, `descripcion`, `precio_referencial`, `cantidad_minima`, `disponible`, `fecha_actualizacion`. Un proveedor tiene muchos productos. |
| `producto_proveedor_temporada` | tabla nueva (N a N) | 3 | `id`, `producto_id` FK→producto_proveedor, `temporada_id` FK→temporada; único (`producto_id`, `temporada_id`). |
| `producto_proveedor.prenda_id` | columna, admite nulo | 3 | Correspondencia con el catálogo: un producto corresponde a 0..1 prenda; una prenda puede tener varios productos. La define la tienda. |
| `detalle_compra.producto_proveedor_id` | columna nueva, admite nulo | 3 | De qué producto ofrecido partió la línea (0..1; nulo si el proveedor no tenía oferta). |
| `detalle_venta.promocion_id` | columna nueva, admite nulo | 3 | Promoción que originó el descuento de la línea (0..1). |
| `proveedor.usuario_id` | columna nueva, admite nulo, única | 3 | Cuenta con la que el proveedor entra a su portal (0..1 a 0..1 con `usuario`). La unicidad va en el modelo para bases nuevas; en una base migrada con `ALTER` la impone el servicio. |
| `permiso`, `rol_permiso`, `bitacora`, `recuperacion_contrasena` | tablas | 1 y 2 | Ya existían antes de este ciclo pero **no están en el diagrama**: permisos por rol, bitácora y recuperación de contraseña (`models/seguridad.py`). |

`promocion` y `promocion_prenda` ya estaban en el diagrama y no cambiaron.
No se usa Alembic: `create_all` crea las tablas nuevas y `core/migraciones.py`
agrega las columnas a las bases que ya existen (Neon y SQLite) con `ALTER TABLE`
idempotentes, al arrancar la API y al correr el seed.

### Variables de entorno y dependencias

**No hay dependencias nuevas**: `backend/requirements.txt` y `web/package.json`
quedaron igual (CSV y gráficos se resolvieron sin librerías).

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
- **84 ventas** de los últimos 45 días por caja, web y app, con sus pagos,
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
    ├── catalogo/  tienda/           catálogo público, carrito y mis reservas
    ├── admin/                       panel: usuarios, roles, bitácora, catálogos base,
    │                                prendas y promociones (CU18)
    ├── inventario/                  inventario, movimientos, compras y
    │                                oferta de proveedores (CU9 -> CU10)
    ├── reservas/  caja/             reservas de la sucursal y venta en caja
    ├── reportes/                    dashboard y reportes (CU19)
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
   pantallas contra ese contrato sin esperar el código del backend.

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
