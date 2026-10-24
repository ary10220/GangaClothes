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

