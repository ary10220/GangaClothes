# REPARTO DE TAREAS — Parcial 2 (SI2 · UAGRM)

> **Proyecto nuevo desde cero.** NO es continuación del parcial 1.
> SaaS multitenant para tiendas de ropa. Metodología **ICONIX** (no PUDS).
> Stack: FastAPI + SQLAlchemy + PostgreSQL · Angular · Flutter. Monorepo
> con `backend/`, `web/`, `mobile/`, `docs/`.

Equipo: **Ariany** (Integrante 1) · **Compañera** (Integrante 2).

---

## Fechas clave

| Hito | Fecha |
|---|---|
| Presentación #1 | dom **25/10/2025** |
| Presentación #2 | dom **01/11/2025** |
| Presentación #3 | dom **08/11/2025** |
| Defensa final | mar **10/11/2025** |

---

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

> CU-06 y CU-12+ todavía sin asignar. CU-18 a CU-23 (operación sin conexión
> + sincronización) se dejan **previstos en el esquema** pero no se
> implementan en este parcial.

---

## Cimientos que ya quedan a mi cargo (bloque A y B)

1. **Esqueleto monorepo + backend por módulos** — `core/` (config, DB,
   seguridad, dependencias), `models/`, `modules/<cu>/router + service +
   schemas`.
2. **Multitenancy central** — esquema compartido con `tenant_id`:
   - Dependencia que extrae `tenant_id` del JWT y lo inyecta.
   - Helper de consulta base que filtra por tenant **por diseño** (olvidarlo
     es imposible).
   - Todas las UNIQUE por tenant: `UNIQUE(tenant_id, email)`,
     `UNIQUE(tenant_id, codigo)`, etc. **Nunca globales.**
   - Scope aparte para el **Superadministrador de plataforma** (opera por
     encima de los tenants).
3. **Preparación offline (sin implementar sync)** — estados `LOCAL`,
   `ENVIADA`, `CONFIRMADA`, `RECHAZADA`, `EN_CONFLICTO` + idempotencia por
   `UNIQUE(tenant_id, uuid_operacion)` en tablas de operaciones.
4. **Semillas de demo** — mínimo **2 empresas contratantes** distintas, cada
   una con sucursales, usuarios y plan + planes básico/profesional/
   empresarial con límites distintos + 1 superadmin de plataforma.

---

## Reglas de trabajo

1. **Nada se commitea ni se sube sin tu luz verde.**
2. `.claude/` y `CLAUDE.md` en `.gitignore` **desde el primer commit**.
3. Nunca `Co-Authored-By: Claude` ni footer "Generated with Claude Code".
4. Avanzar de corrido; explicar decisiones al final, no entre pasos.
5. README se mantiene vivo con lo que se va construyendo (en especial la
   explicación de cómo queda garantizado el aislamiento).

---

## Verificación que me vas a pedir al cerrar los cimientos

1. Registrar un tenant nuevo con su admin inicial y plan.
2. Login en tenant A y tenant B → cada uno ve **solo** lo suyo; acceder por
   id directo a un recurso ajeno debe dar **403 o 404**.
3. Consultar estado de suscripción con consumo real contra límites
   (ej. "3 de 5 sucursales usadas").
4. Llegar al límite del plan al crear la 6ª sucursal → rechazo con mensaje
   claro que nombre el límite y el plan.
5. Superadministrador viendo y administrando todas las empresas.
