# GangaSaaS — Parcial 2 SI2 · UAGRM

SaaS multitenant para tiendas de ropa. **Proyecto nuevo desde cero.**
Metodología ICONIX. Stack FastAPI + SQLAlchemy + PostgreSQL (SQLite local
por defecto) · Angular · Flutter.

Este README documenta los cimientos que ya quedan en pie: **multitenancy
central** + los CU que lleva Ariany (CU-01, CU-02, CU-04, CU-05, CU-07).
La compañera consume la API desde el móvil/web.

## 1. Cómo se garantiza el aislamiento entre tenants

Esquema compartido con discriminador `tenant_id`. El aislamiento se aplica
**en el motor del ORM**, no en cada consulta:

- `TenantMixin` ([backend/app/core/database.py:22](backend/app/core/database.py#L22))
  marca los modelos que tienen `tenant_id`. Lo heredan: `User`, `Sucursal`,
  `Suscripcion`, `OperacionLog`.
- Un listener de SQLAlchemy sobre `do_orm_execute`
  ([backend/app/core/database.py:46](backend/app/core/database.py#L46))
  intercepta todo `SELECT`, `UPDATE` y `DELETE` del ORM y le mete, vía
  `with_loader_criteria`, un `WHERE tenant_id = scope.tenant_id`.
- El `tenant_id` sale del JWT en
  [backend/app/core/deps.py](backend/app/core/deps.py) y queda guardado en
  `session.info["tenant_scope"]` antes de ejecutar la query.
- El superadmin (`kind="super"`) no tiene `tenant_id` y el filtro **no se
  aplica** — opera por encima de todas las empresas.
- Todas las UNIQUE son por tenant: `UNIQUE(tenant_id, email)`,
  `UNIQUE(tenant_id, codigo)`, `UNIQUE(tenant_id, uuid_operacion)`. Nunca
  globales (excepto NIT del propio tenant y email del superadmin).

**Por qué "imposible por diseño"**: olvidarse del filtro en un servicio no
tiene efecto. El filtro no vive en el servicio, vive en la ejecución del
ORM. Para saltearlo habría que usar SQL en crudo o entrar sin JWT —
cualquiera de las dos deja huella y no pasa por la capa normal.

## 2. Cómo se identifica el tenant al iniciar sesión (CU-02)

**Decisión**: `codigo_tenant` + `email` + `password` en el formulario de
login (`POST /api/v1/auth/login`).

Comparación:

| Opción | Pro | Contra |
|---|---|---|
| **Código de tenant en el form** ✅ | Explícito, se defiende en vivo. No necesita infra extra. Permite que **el mismo correo** exista en dos empresas distintas. | Un campo más en el form. |
| Subdominio (`luna.saas.com`) | Elegante, "SaaS clásico". | Exige DNS + wildcard + reverse proxy local. En una demo rompe más que ayuda. |
| Correo globalmente único | Un solo campo, muy limpio. | Rompe la premisa real: Ana puede trabajar en Boutique Luna y además en Moda Andina — y en multitenant se asume que un correo pertenece a una empresa, no al SaaS. |

El superadministrador se autentica aparte en `POST /api/v1/auth/super/login`,
sin tenant.

## 3. Arquitectura por módulos

```
backend/app/
├── core/
│   ├── config.py        settings (DATABASE_URL, JWT, CORS)
│   ├── database.py      engine, Base, TenantMixin, listener multitenant
│   ├── security.py      bcrypt + JWT
│   └── deps.py          get_db, get_scope, require_super, require_tenant, require_roles
├── models/              Tenant, Plan, Suscripcion, User, SuperAdmin, Sucursal, OperacionLog
├── modules/
│   ├── tenants/         CU-01 (super crea empresa + admin + plan)
│   ├── auth/            CU-02 (login tenant/super + /me)
│   ├── sucursales/      CU-04 (CRUD + rechazo por límite)
│   ├── planes/          catálogo público (autenticado)
│   └── suscripciones/   CU-05 contratar + CU-07 estado y consumo
└── seeds/demo.py        2 empresas + 3 planes + superadmin
```

## 4. Correr en local

```bash
cd parcial2/backend
python -m venv .venv
.venv\Scripts\activate         # Windows PowerShell
pip install -r requirements.txt
python -m app.seeds.demo       # crea tablas y semillas
uvicorn app.main:app --reload  # http://127.0.0.1:8000/docs
```

Config por variables de entorno (opcional):

```
DATABASE_URL=postgresql+psycopg2://user:pass@host/db  # dev local usa sqlite
JWT_SECRET=algo-largo-y-aleatorio
CORS_ORIGINS=http://localhost:4200,http://localhost:5173
```

## 5. Credenciales de la demo

- **Superadmin**: `root@plataforma.bo` / `SuperSegura123`
- **Tenant `luna`** (plan Profesional): admin `ana@boutique-luna.bo` / `Luna12345`
- **Tenant `andina`** (plan Básico, 1 sucursal máx.): admin `rodrigo@modaandina.bo` / `Andina12345`

## 6. Verificación de los cimientos (lo que se enseña en vivo)

1. **Registrar un tenant** — super hace `POST /api/v1/tenants` con razón
   social, NIT, código, admin inicial y `plan_codigo="profesional"`.
2. **Aislamiento** — login en `luna` y en `andina`:
   `GET /api/v1/sucursales` devuelve **solo las propias**; pedir por id una
   sucursal del otro tenant devuelve **404** (no 403 — ni enteramos de que
   el id existe en otra empresa).
3. **Estado y consumo** — `GET /api/v1/suscripciones/estado` del tenant
   muestra `plan`, `fecha_fin` y `consumos: [{recurso:"sucursales",
   actual:2, limite:3, disponible:1}, ...]`.
4. **Rechazo por límite** — con el plan Básico (1 sucursal), crear una
   segunda sucursal responde `409 CONFLICT` con mensaje:
   `"Limite alcanzado para sucursales: 1 de 1 segun el plan 'Basico'.
   Contrata un plan superior para seguir dando de alta sucursales."`
5. **Superadmin** — `GET /api/v1/tenants` lista todas las empresas con su
   plan vigente y fecha de fin.

## 7. Preparación para CU-18 a CU-23 (sin implementar)

Tabla `operaciones_log` con:

- `UNIQUE(tenant_id, uuid_operacion)` → **idempotencia**: reenviar la misma
  operación no la duplica.
- `estado` ∈ `{LOCAL, ENVIADA, CONFIRMADA, RECHAZADA, EN_CONFLICTO}` →
  máquina de estados para sincronización offline.

Ver [backend/app/models/operacion.py](backend/app/models/operacion.py).

## 8. Reparto de CUs

Ver [docs/Reparto.md](docs/Reparto.md).

---

## 9. Guía para la compañera — ponerlo en tu compu y consumir la API

Esta sección es la que te deja arrancar de cero sin preguntarle nada a Ariany.

### 9.1 Prerrequisitos

- **Python 3.12** (3.11 también anda) — [python.org/downloads](https://www.python.org/downloads/).
- **Git** — [git-scm.com/downloads](https://git-scm.com/downloads).
- Un editor cualquiera (VS Code, PyCharm…).

Verificar en consola:

```bash
python --version   # Python 3.12.x
git --version
```

### 9.2 Clonar el repo y cambiar a la rama

El backend vive **dentro del repo GangaClothes**, en la carpeta `parcial2/`,
en la rama `ariany-ciclo`.

```bash
git clone https://github.com/ary10220/GangaClothes.git
cd GangaClothes
git fetch origin
git checkout ariany-ciclo
cd parcial2/backend
```

Cuando Ariany haga nuevos cambios, tirar:

```bash
git pull origin ariany-ciclo
```

### 9.3 Levantar el backend en tu máquina

```bash
# 1) Virtualenv aislado para no mezclar paquetes
python -m venv .venv
.venv\Scripts\activate         # Windows PowerShell
# source .venv/bin/activate    # Linux/Mac

# 2) Dependencias
pip install -r requirements.txt

# 3) Crear tablas + semillas (2 empresas, 3 planes, superadmin)
python -m app.seeds.demo

# 4) Levantar la API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

El `--host 0.0.0.0` es importante: deja que tu **móvil físico** o un
emulador vean la API. Si solo vas a probar desde el navegador en la misma
compu, podés dejar `--host 127.0.0.1`.

**Comprobación**: abrir [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
→ aparece Swagger con todos los endpoints. Clickeá "Try it out" en
`POST /api/v1/auth/login` y mandá el body de ejemplo de 9.6.

### 9.4 Cómo conectar tu app a esta API

**Base URL**: todas las rutas cuelgan de `/api/v1/`. La URL completa
depende de desde dónde consumas:

| Cliente | Base URL |
|---|---|
| Angular en la misma PC (`ng serve`) | `http://localhost:8000/api/v1` |
| Flutter — emulador Android | `http://10.0.2.2:8000/api/v1` (el emulador mapea `10.0.2.2` → tu PC) |
| Flutter — emulador iOS | `http://localhost:8000/api/v1` |
| Flutter — móvil físico en la misma Wi-Fi | `http://<IP-LAN-de-tu-PC>:8000/api/v1` (buscar con `ipconfig`) |

**CORS**: por defecto el backend acepta `*`. Si querés restringir, levantalo así:

```bash
set CORS_ORIGINS=http://localhost:4200,http://localhost:5173
uvicorn app.main:app --reload --host 0.0.0.0
```

### 9.5 Autenticación — qué guardar y qué mandar

1. El cliente hace `POST /api/v1/auth/login` con `codigo_tenant`, `email` y `password`.
2. La respuesta trae `access_token` (JWT). **Lo guardás** (localStorage / secure storage).
3. En cada request posterior mandás el header:

   ```
   Authorization: Bearer <access_token>
   ```

4. Si el server responde `401`, el token venció o es inválido → mandás al login.

El token expira a las **8 horas** (configurable con `JWT_EXP_MINUTES`).

### 9.6 Ejemplos de request/response

**Login como tenant** — `POST /api/v1/auth/login`

```json
// Request
{
  "codigo_tenant": "luna",
  "email": "ana@boutique-luna.bo",
  "password": "Luna12345"
}
// Response 200
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
  "token_type": "bearer",
  "kind": "tenant",
  "tenant_id": 1,
  "tenant_codigo": "luna",
  "user_id": 1,
  "nombre": "Ana Luna",
  "roles": ["admin"]
}
```

**Login como superadmin** — `POST /api/v1/auth/super/login`

```json
{ "email": "root@plataforma.bo", "password": "SuperSegura123" }
```

**Quién soy** — `GET /api/v1/auth/me` (header con Bearer)

**Listar sucursales del tenant logueado** — `GET /api/v1/sucursales`

```json
// Response 200
[
  { "id": 1, "codigo": "suc-01", "nombre": "Luna Centro", "ciudad": "Santa Cruz",
    "direccion": "Av. Monseñor Rivero 123", "horario": "10:00-20:00",
    "estado": "activa", "activo": true, "created_at": "2026-10-23T18:30:00Z" }
]
```

**Crear sucursal** — `POST /api/v1/sucursales` (rol `admin`)

```json
{ "codigo": "suc-02", "nombre": "Luna Equipetrol", "ciudad": "Santa Cruz",
  "direccion": "Av. San Martin 500", "horario": "10:00-22:00" }
```

**Estado y consumo del plan (CU-07)** — `GET /api/v1/suscripciones/estado`

```json
{
  "tiene_suscripcion": true,
  "plan": { "codigo": "profesional", "nombre": "Profesional",
            "max_sucursales": 3, "max_usuarios": 10, "max_productos": 1000,
            "modulos": ["ventas","inventario","reportes","promociones"],
            "precio_mensual": 49.0, "activo": true },
  "fecha_inicio": "2026-10-23", "fecha_fin": "2026-11-22", "estado": "activa",
  "consumos": [
    { "recurso": "sucursales", "actual": 2, "limite": 3, "disponible": 1 },
    { "recurso": "usuarios",   "actual": 2, "limite": 10, "disponible": 8 }
  ],
  "modulos_habilitados": ["ventas","inventario","reportes","promociones"]
}
```

**Contratar un plan (CU-05)** — `POST /api/v1/suscripciones/contratar` (rol `admin`)

```json
{ "plan_codigo": "empresarial", "duracion_dias": 30 }
```

**Catálogo de planes** — `GET /api/v1/planes` → útil para armar el combo
de "contratar plan" en pantalla.

**Flujo completo con curl**:

```bash
# 1) Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"codigo_tenant":"luna","email":"ana@boutique-luna.bo","password":"Luna12345"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2) Pedir las sucursales con el token
curl http://localhost:8000/api/v1/sucursales -H "Authorization: Bearer $TOKEN"

# 3) Estado del plan
curl http://localhost:8000/api/v1/suscripciones/estado -H "Authorization: Bearer $TOKEN"
```

### 9.7 Códigos de error que tu UI debe manejar

| Código | Qué pasó | Qué mostrar al usuario |
|---|---|---|
| **401** | Sin token, token malo o vencido | "Tu sesión expiró, iniciá sesión de nuevo." → al login |
| **403** | Rol insuficiente (ej. `encargado` creando sucursal) | "No tenés permiso para esta acción." |
| **404** | Recurso inexistente **o de otro tenant** | "No se encontró el recurso." (no decir "es de otra empresa") |
| **409** | Conflicto de negocio — **lo más importante**: límite del plan superado | Mostrar `detail` tal cual: `"Limite alcanzado para sucursales: 1 de 1 segun el plan 'Basico'. Contrata un plan superior..."` |
| **422** | Validación de pydantic (campo faltante o mal formato) | Resaltar el campo que viene en `detail[0].loc` |

El cuerpo de un error siempre es:

```json
{ "detail": "mensaje humano" }
// o para 422:
{ "detail": [ { "type": "value_error", "loc": ["body","email"], "msg": "..." } ] }
```

### 9.8 Credenciales para probar

- Super: `root@plataforma.bo` / `SuperSegura123`
- Admin Luna (Profesional, 3 sucursales): `ana@boutique-luna.bo` / `Luna12345`
- Encargado Luna: `encargado@boutique-luna.bo` / `Luna12345`
- Admin Andina (Básico, 1 sucursal — probar rechazo por límite): `rodrigo@modaandina.bo` / `Andina12345`

Ambos tenants usan el campo `codigo_tenant`: `"luna"` o `"andina"`.

### 9.9 Troubleshooting

- **`pip install` falla con `bcrypt`** — ya está pineado a `4.0.1` en
  `requirements.txt`. Si igual rompe: `pip install bcrypt==4.0.1 --force-reinstall`.
- **`email-validator` rechaza correos con `.local`** — es a propósito, usá
  TLDs reales (`.bo`, `.com`).
- **Puerto 8000 ocupado** — `uvicorn ... --port 8001` y actualizá la base URL.
- **El móvil no se conecta** — chequear que la PC y el móvil estén en la
  misma Wi-Fi, firewall abierto en el puerto, y usar la IP de LAN
  (`ipconfig` en Windows) en vez de `localhost`.
- **"Token invalido: Subject must be a string"** — ya está arreglado: el
  JWT guarda `sub` como string. Si lo ves, estás contra una versión vieja
  del backend: `git pull`.

### 9.10 Para tus CU-03 / 08 / 09 / 10 / 11

Cuando armes tus endpoints:

- Hereda tus modelos de `TenantMixin` si deben aislarse por empresa
  (todo lo que no sea catálogo global).
- Usá `Depends(require_tenant)` o `Depends(require_roles("admin"))` en los
  routers; el `scope.tenant_id` queda listo para filtrar.
- Si un recurso tiene un límite por plan (productos, usuarios, lo que sea),
  llamá a `exigir_capacidad(db, scope.tenant_id, "<recurso>")` antes de
  crear — devuelve 409 con mensaje consistente al resto del sistema.
- Agregá tus endpoints documentándolos acá debajo cuando los termines.

---

## 10. Endpoints de CU-09 — Categorías, Tallas, Colores y Temporadas

Aislamiento completo por `tenant_id` heredando de `TenantMixin`.
- Lectura (`GET`): cualquier usuario autenticado del tenant (`Depends(require_tenant)`).
- Escritura (`POST`, `PATCH`, `DELETE`): administradores del tenant (`Depends(require_roles("admin"))`).
- Duplicados en el mismo tenant devuelven `409 CONFLICT`. Mismo nombre en empresas distintas es permitido.
- Acceso o modificación por id directo de otra empresa devuelve `404 NOT FOUND`.

### 10.1 Categorías (`/api/v1/categorias`)
- `GET /api/v1/categorias`: Lista categorías del tenant.
- `POST /api/v1/categorias`: Crea categoría.
  - Body: `{"nombre": "Poleras", "descripcion": "Poleras y camisetas", "activo": true}`
- `GET /api/v1/categorias/{id}`: Detalle de categoría.
- `PATCH /api/v1/categorias/{id}`: Actualiza campos (`nombre`, `descripcion`, `activo`).
- `DELETE /api/v1/categorias/{id}`: Elimina categoría.

### 10.2 Tallas (`/api/v1/tallas`)
- `GET /api/v1/tallas`: Lista tallas ordenadas por `orden, id`.
- `POST /api/v1/tallas`: Crea talla.
  - Body: `{"nombre": "M", "orden": 2, "activo": true}`
- `GET /api/v1/tallas/{id}`: Detalle de talla.
- `PATCH /api/v1/tallas/{id}`: Actualiza talla.
- `DELETE /api/v1/tallas/{id}`: Elimina talla.

### 10.3 Colores (`/api/v1/colores`)
- `GET /api/v1/colores`: Lista colores del tenant.
- `POST /api/v1/colores`: Crea color.
  - Body: `{"nombre": "Rojo", "codigo_hex": "#FF0000", "activo": true}`
- `GET /api/v1/colores/{id}`: Detalle de color.
- `PATCH /api/v1/colores/{id}`: Actualiza color.
- `DELETE /api/v1/colores/{id}`: Elimina color.

### 10.4 Temporadas (`/api/v1/temporadas`)
- `GET /api/v1/temporadas`: Lista temporadas del tenant.
- `POST /api/v1/temporadas`: Crea temporada.
  - Body: `{"nombre": "Verano 2026", "fecha_inicio": "2026-01-01", "fecha_fin": "2026-03-31", "activo": true}`
- `GET /api/v1/temporadas/{id}`: Detalle de temporada.
- `PATCH /api/v1/temporadas/{id}`: Actualiza temporada.
- `DELETE /api/v1/temporadas/{id}`: Elimina temporada.

---

## 11. Endpoints de CU-03 — Administrar Usuarios y Roles del Tenant (`/api/v1/usuarios`)

Aislamiento completo por `tenant_id` y control por rol `admin`.
- Solo administradores del tenant (`Depends(require_roles("admin"))`) pueden acceder y gestionar usuarios.
- El correo tiene `UNIQUE(tenant_id, email)`: el mismo correo puede existir en dos empresas distintas sin conflicto.
- Si se intenta dar de alta un usuario superando el límite del plan contratado (ej. Básico máx 3 usuarios), el backend devuelve `409 CONFLICT` con mensaje detallado.
- La contraseña se guarda con hash seguro (`bcrypt`).
- Los roles disponibles son: `admin`, `encargado`, `cajero`.
- Soporta tanto `PATCH` como `PUT` para actualización y reactivación/archivado de usuarios.

### 11.1 Endpoints
- `GET /api/v1/usuarios`: Lista los usuarios del tenant autenticado.
- `POST /api/v1/usuarios`: Da de alta un nuevo usuario.
  - Body: `{"nombre": "Carlos", "apellido": "Vaca", "email": "carlos@boutique-luna.bo", "password": "Password123", "telefono": "70099887", "rol": "cajero", "activo": true}`
- `GET /api/v1/usuarios/{id}`: Detalle del usuario.
- `PATCH /api/v1/usuarios/{id}` / `PUT /api/v1/usuarios/{id}`: Actualiza datos (rol, nombre, apellido, teléfono, activo, contraseña).
- `DELETE /api/v1/usuarios/{id}`: Elimina el usuario del tenant (no permite autoeliminarse al admin logueado).

---

## 12. Endpoints de CU-10 — Gestionar Proveedores (`/api/v1/proveedores`)

Aislamiento completo por `tenant_id` y control por rol `admin` / `encargado`.
- Lectura (`GET`): cualquier usuario del tenant (`Depends(require_tenant)`).
- Creación y edición (`POST`, `PATCH`, `PUT`): usuarios con rol `admin` o `encargado`.
- Eliminación (`DELETE`): administradores (`admin`).
- Restricción `UNIQUE(tenant_id, nombre)`: dos empresas pueden tener proveedores con nombres similares sin conflicto; duplicados dentro del mismo tenant devuelven `409 CONFLICT`.

### 12.1 Endpoints
- `GET /api/v1/proveedores`: Lista proveedores del tenant autenticado.
- `POST /api/v1/proveedores`: Registra un proveedor.
  - Body: `{"nombre": "Textiles Andinos SRL", "nit": "1020304025", "contacto": "Rosa Mamani", "telefono": "70012345", "email": "ventas@proveedor.bo", "direccion": "Av. Principal 456", "activo": true}`
- `GET /api/v1/proveedores/{id}`: Detalle de proveedor.
- `PATCH /api/v1/proveedores/{id}` / `PUT /api/v1/proveedores/{id}`: Actualiza proveedor.
- `DELETE /api/v1/proveedores/{id}`: Elimina proveedor.

---

## 13. Endpoints de CU-08 — Gestionar Productos del Catálogo y Variantes (`/api/v1/productos` y alias `/api/v1/prendas`)

Aislamiento completo por `tenant_id` y control por rol `admin` / `encargado`.
- Soporta tanto `/api/v1/productos` como el alias `/api/v1/prendas` para plena compatibilidad con el frontend Angular existente.
- Entidades vinculadas con `TenantMixin`: `Producto` y `Variante`.
- Relaciones validadas: `categoria_id`, `temporada_id`, `proveedor_id`, `talla_id`, `color_id` deben pertenecer a la misma empresa (`404` si pertenecen a otro tenant o no existen).
- Restricciones de unicidad:
  - `UNIQUE(tenant_id, nombre)`: Unicidad de nombre de producto por tenant.
  - `UNIQUE(tenant_id, sku)`: Código de barras / SKU único por tenant.
  - `UNIQUE(producto_id, talla_id, color_id)`: No se permiten variantes duplicadas para un mismo producto.
- Control de suscripción: Valida `exigir_capacidad(db, tenant_id, "productos")` comparando contra `plan.max_productos` (`409 CONFLICT` al superar límite).
- Estado de publicación: Endpoints dedicados para activar/desactivar publicación en tienda en línea (`/publicar`, `/despublicar`).

### 13.1 Endpoints de Producto
- `GET /api/v1/productos` (o `/api/v1/prendas`): Lista productos con filtros opcionales (`categoria_id`, `temporada_id`, `proveedor_id`, `publicado`, `activo`).
- `GET /api/v1/productos/catalogo-interno` (o `/api/v1/prendas/catalogo-interno`): Catálogo para caja y compras (prendas activas con variantes).
- `POST /api/v1/productos`: Da de alta un nuevo producto y sus variantes opcionales.
  - Body:
    ```json
    {
      "nombre": "Jean Slim Fit Denim",
      "categoria_id": 1,
      "temporada_id": 1,
      "proveedor_id": 1,
      "descripcion": "Jean stretch de mezclilla azul oscuro",
      "marca": "Luna Denim",
      "genero": "unisex",
      "precio_venta": 180.0,
      "costo": 70.0,
      "activo": true,
      "publicado": false,
      "variantes": [
        {
          "talla_id": 1,
          "color_id": 2,
          "sku": "LUNA-JEAN-S-NEG",
          "precio_adicional": 0.0
        }
      ]
    }
    ```
- `GET /api/v1/productos/{id}`: Detalle del producto con sus variantes.
- `PATCH /api/v1/productos/{id}` / `PUT /api/v1/productos/{id}`: Actualización parcial o completa.
- `DELETE /api/v1/productos/{id}`: Elimina el producto y sus variantes en cascada (rol `admin`).
- `POST /api/v1/productos/{id}/publicar`: Publica el producto en la tienda (`{"confirmar_sin_stock": true}`).
- `POST /api/v1/productos/{id}/despublicar`: Retira el producto de la tienda.

### 13.2 Endpoints de Variantes
- `GET /api/v1/productos/{producto_id}/variantes`: Lista variantes de un producto.
- `POST /api/v1/productos/{producto_id}/variantes`: Agrega una variante al producto.
  - Body: `{"talla_id": 2, "color_id": 1, "sku": "LUNA-POL-M-BLA", "precio_adicional": 5.0, "activo": true}`
- `GET /api/v1/productos/variantes/{variante_id}`: Detalle de variante.
- `PATCH /api/v1/productos/variantes/{variante_id}` / `PUT /api/v1/productos/variantes/{variante_id}`: Actualiza variante (SKU, precio adicional, imagen, estado).
- `DELETE /api/v1/productos/variantes/{variante_id}`: Elimina la variante (rol `admin`).

---

## 14. Endpoints de CU-11 — Gestionar Clientes del Tenant (`/api/v1/clientes`)

Aislamiento completo por `tenant_id` y permisos para el personal del tenant (`admin`, `encargado`, `cajero`).
- Entidad `Cliente` vinculada con `TenantMixin`.
- Cada empresa gestiona su propia cartera de clientes (compradores en tienda física, compras web y reservas).
- Restricciones de unicidad por tenant:
  - `UNIQUE(tenant_id, email)`: No se permiten correos duplicados dentro de la misma empresa (`409 CONFLICT`).
  - `UNIQUE(tenant_id, ci_nit)`: No se permiten CI/NIT duplicados dentro de la misma empresa (`409 CONFLICT`).
  - Diferentes empresas pueden registrar clientes con el mismo correo o CI/NIT de forma independiente sin conflicto.
- Búsqueda y filtrado:
  - Búsqueda textual mediante parámetro `q` sobre `nombre`, `apellido`, `ci_nit`, `telefono` y `email`.
  - Filtro por `tipo` de cliente (`regular`, `mayorista`, `vip`) y por estado `activo`.
- Roles y permisos:
  - Lectura (`GET`): cualquier usuario autenticado del tenant (`Depends(require_tenant)`).
  - Creación y edición (`POST`, `PATCH`, `PUT`): usuarios con rol `admin`, `encargado` o `cajero`.
  - Eliminación (`DELETE`): administradores o encargados (`admin`, `encargado`).
  - Sin token: rechazo con `401 UNAUTHORIZED`.

### 14.1 Endpoints
- `GET /api/v1/clientes`: Lista clientes del tenant autenticado con filtros opcionales (`q`, `tipo`, `activo`).
- `POST /api/v1/clientes`: Da de alta un nuevo cliente.
  - Body:
    ```json
    {
      "nombre": "Valeria",
      "apellido": "Morales",
      "ci_nit": "8765432",
      "telefono": "78945612",
      "email": "valeria.morales@gmail.com",
      "direccion": "Condominio La Riviera Dpto 4B",
      "ciudad": "Santa Cruz",
      "tipo": "vip",
      "notas": "Prefiere vestidos largos y colores oscuros",
      "activo": true
    }
    ```
- `GET /api/v1/clientes/{id}`: Detalle del cliente. Devuelve `404 NOT FOUND` si pertenece a otra empresa.
- `PATCH /api/v1/clientes/{id}` / `PUT /api/v1/clientes/{id}`: Actualización de datos (parcial o completa).
- `DELETE /api/v1/clientes/{id}`: Elimina el cliente del tenant.





