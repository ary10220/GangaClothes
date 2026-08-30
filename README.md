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
python seed.py                # crea tablas + datos de demostración
uvicorn app.main:app --reload
```

Abrir **http://localhost:8000/docs** → ahí está TODO el contrato de la API
(lo implementado y lo pendiente con su responsable e iteración).

Usuarios de prueba del seed:

| Correo | Contraseña | Rol |
|---|---|---|
| admin@gangaclothes.com | Admin123 | administrador |
| encargado@gangaclothes.com | Encargado123 | encargado |
| cajero@gangaclothes.com | Cajero123 | cajero |

Sin configurar nada usa **SQLite local** (`gangaclothes_dev.db`). Para usar
PostgreSQL real: copiar `.env.example` a `.env` y pegar la URL de Neon.

### Estructura del backend (patrón por módulos)

```
backend/app/
├── core/        config, conexión BD, seguridad JWT, dependencias (roles)
├── models/      las 28 tablas SQLAlchemy (espejo del diagrama de clases)
└── modules/     un módulo por paquete del análisis:
    ├── auth/            router + schemas + service   ← PATRÓN DE REFERENCIA
    ├── catalogos_base/  CRUD generado con la fábrica (comunes.py)
    ├── usuarios/  prendas/                           ← implementados
    └── inventario/ reservas/ ventas/ pagos/
        promociones/ reportes/ ia/                    ← stubs con plan y responsable
```

Regla: los módulos con lógica de negocio (inventario, reservas, ventas, pagos)
se implementan con `router.py` + `service.py` copiando el patrón de `auth/`.
Los CRUD simples usan la fábrica `modules/comunes.py`.

---

## 2. Crear el frontend web (Angular) — Ariany

```bash
npm install -g @angular/cli
rm -rf web            # está vacío, ng new necesita crearlo
ng new web --routing --style=css --skip-git
cd web && npm start
```

Estructura de features acordada:

```
web/src/app/
├── core/        auth.service.ts, jwt.interceptor.ts, auth.guard.ts, api.ts
├── shared/      componentes comunes
└── features/
    ├── catalogo/  carrito/          ← Integrante 2
    └── admin/  inventario/  caja/   ← Integrante 1
```

`src/app/core/api.ts` (URL base):

```ts
export const API_URL = 'http://localhost:8000/api'; // en Vercel: URL de Render
```

`src/app/core/auth.service.ts` (mínimo para arrancar):

```ts
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { API_URL } from './api';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  login(email: string, password: string) {
    return this.http.post<any>(`${API_URL}/auth/login`, { email, password });
  }
  guardar(token: string, usuario: any) {
    localStorage.setItem('token', token);
    localStorage.setItem('usuario', JSON.stringify(usuario));
  }
  get token() { return localStorage.getItem('token'); }
  get roles(): string[] { return JSON.parse(localStorage.getItem('usuario') ?? '{}').roles ?? []; }
  salir() { localStorage.clear(); }
}
```

`src/app/core/jwt.interceptor.ts` (agrega el token a cada petición):

```ts
import { HttpInterceptorFn } from '@angular/common/http';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem('token');
  return next(token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req);
};
// registrar en app.config.ts:
// provideHttpClient(withInterceptors([jwtInterceptor]))
```

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
   Variables: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS=*`.
   Luego correr el seed una vez desde la Shell de Render: `python seed.py`.
3. **Vercel** (web): importar el repo → Root Directory `web` → framework Angular.
4. **APK**: `flutter build apk --release` → subir a un Release de GitHub → ese
   enlace + QR van en el documento.

---

## 6. Tareas Semana 1 (Iteración 1 → Presentación #1, sáb 05/09)

> Ver `docs/REPARTO_TAREAS.md` para la lista completa de diagramas y pantallas
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
