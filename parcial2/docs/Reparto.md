# REPARTO DE TAREAS — Parcial 2 (SI2 · UAGRM)

> **Proyecto nuevo desde cero.** NO es continuación del parcial 1.
> SaaS multitenant para tiendas de ropa. Metodología **ICONIX** (no PUDS).
> Stack: FastAPI + SQLAlchemy + PostgreSQL · Angular · Flutter.

Equipo: **Ariany** (Integrante 1) · **Compañera** (Integrante 2).

## Fechas clave

| Hito | Fecha |
|---|---|
| Presentación #1 | dom 25/10/2025 |
| Presentación #2 | dom 01/11/2025 |
| Presentación #3 | dom 08/11/2025 |
| Defensa final | mar 10/11/2025 |

## Reparto de Casos de Uso

| CU | Nombre | Responsable |
|---|---|---|
| CU-01 | Registrar empresa contratante (tenant) | **Ariany** |
| CU-02 | Autenticar usuario con contexto de tenant | **Ariany** |
| CU-03 | *(a definir con la compañera)* | Compañera |
| CU-04 | Gestionar sucursales del tenant | **Ariany** |
| CU-05 | Contratar plan de suscripción | **Ariany** |
| CU-07 | Consultar estado y límites del plan | **Ariany** |
| CU-08 | *(a definir con la compañera)* | Compañera |
| CU-09 | *(a definir con la compañera)* | Compañera |
| CU-10 | *(a definir con la compañera)* | Compañera |
| CU-11 | *(a definir con la compañera)* | Compañera |

CU-18 a CU-23 (operación sin conexión + sincronización) **no se implementan**
este parcial, pero quedan previstos en el esquema (`OperacionLog` +
`UNIQUE(tenant_id, uuid_operacion)` + estados `LOCAL/ENVIADA/CONFIRMADA/
RECHAZADA/EN_CONFLICTO`).

## Reglas de trabajo

1. Nada se commitea ni se sube sin la luz verde de Ariany.
2. `.claude/` y `CLAUDE.md` en `.gitignore` **desde el primer commit**.
3. Nunca `Co-Authored-By: Claude` ni "Generated with Claude Code" en commits
   de este repo.
4. Ariany trabaja en rama `ariany-ciclo`; la compañera en su rama.
   La compañera **consume la API** desde su parte.

## Verificación de los cimientos (lo que se demuestra en vivo)

1. Registrar un tenant nuevo con admin inicial y plan.
2. Login en tenant A y en tenant B: cada uno ve **solo** sus sucursales y
   usuarios; pedir por id directo un recurso del otro tenant → **404**.
3. Consultar estado de suscripción con consumo real contra los límites.
4. Llegar al límite de sucursales del plan → rechazo con mensaje claro.
5. Superadmin viendo y administrando todas las empresas.
