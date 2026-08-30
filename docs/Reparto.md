# REPARTO DEFINITIVO DE TAREAS — GangaClothes
# Equipo: Ariany (Integrante 1) + Compañero (Integrante 2)

## REGLA: Backend ya está hecho. Ambos hacen pantallas + diagramas.

---

## PANTALLAS (no cambian — cada uno programa su plataforma)

| Plataforma | Responsable | Pantallas |
|---|---|---|
| Web Angular (admin + cliente) | Ariany | 10 pantallas |
| App Flutter (cliente móvil) | Compañero | 4 pantallas (+AR que es la más difícil) |

---

## DIAGRAMAS — REPARTO TOTAL (3 iteraciones)

### MODELO DE NEGOCIO — 3 diagramas de actividad
| # | Diagrama | Quién |
|---|---|---|
| D1 | Actividad: Reserva → prueba → venta en caja | Compañero |
| D2 | Actividad: Compra digital con pasarela | Compañero |
| D3 | Actividad: Reposición por stock mínimo | Compañero |

### CAPTURA DE REQUISITOS — CU por iteración + general
| # | Diagrama | Quién |
|---|---|---|
| D4 | CU Iteración 1 | Ariany |
| D5 | CU Iteración 2 | Compañero |
| D6 | CU Iteración 3 | Compañero |
| D7 | CU General del Sistema | Ariany |

### MINI-DIAGRAMAS actor→óvalo (28 en total, 1 por CU)
| Rango | Quién | Cantidad |
|---|---|---|
| CU1–CU12 (web admin/encargado/cajero) | Ariany | 12 |
| CU13–CU19 (web cliente + extras) | Compañero | 7 |
| CU20–CU28 (móvil) | Compañero | 9 |
| **Total** | **Ariany 12 · Compañero 16** | **28** |

### ANÁLISIS
| # | Diagrama | Quién |
|---|---|---|
| D9 | Identificar paquetes (5 paquetes con objetivo) | Compañero |
| D10 | Relacionar paquetes ↔ CU (+trace) — 5 diags | Compañero |
| D11 | Vista de paquete (CU dentro de marco) — 5 diags | Compañero |
| D12 | Comunicación It.1 (3 diags) | Ariany |
| D13 | Comunicación It.2 (3 diags) | Compañero |
| D14 | Comunicación It.3 (2 diags) | Compañero |
| D15 | Clases de análisis It.1 | Ariany |
| D16 | Clases de análisis It.2 | Compañero |
| D17 | Clases de análisis It.3 | Compañero |
| D18 | Análisis de paquete (dependencias) | Compañero |

### DISEÑO
| # | Diagrama | Quién |
|---|---|---|
| D19 | Despliegue físico | Ariany |
| D20 | Capas lógico | Ariany |
| D21 | Red | Compañero |
| D22 | Diagrama de clases | ✅ YA HECHO |
| D23 | Secuencia It.1 (3 diags) | Ariany |
| D24 | Secuencia It.2 (3 diags) | Compañero |
| D25 | Secuencia It.3 (2 diags) | Compañero |

### IMPLEMENTACIÓN
| # | Diagrama | Quién |
|---|---|---|
| D26 | Arquitectura del sistema | Ariany |
| D27 | Componentes: Seguridad y usuarios | Ariany |
| D28 | Componentes: Productos e inventario | Compañero |
| D29 | Componentes: Ventas y carrito | Compañero |

---

## CONTEO FINAL — TODAS LAS ITERACIONES

| Tipo de tarea | Ariany | Compañero |
|---|---|---|
| Pantallas que programa | 10 | 4 (+AR difícil) |
| Diagramas grandes/medianos | 10 | 19 |
| Mini-diagramas actor→óvalo | 12 | 16 |
| **TOTAL TAREAS** | **32** | **39** |

---

## SEMANA 1 — Presentación #1 (sáb 05/09)

### Ariany — Web Angular
1. Login (todos los roles)
2. Dashboard admin (menú lateral según rol)
3. CRUD Categorías
4. CRUD Tallas
5. CRUD Colores
6. CRUD Temporadas
7. CRUD Colecciones
8. CRUD Ciudades y Sucursales
9. CRUD Prendas + Variantes
10. Catálogo público (cliente web)

Diagramas semana 1:
- D4 CU Iteración 1
- D7 CU General del Sistema
- D12 Comunicación It.1

### Compañero — App Flutter
1. Login / Registro
2. Catálogo con filtros
3. Detalle de prenda con disponibilidad por sucursal
4. Prueba técnica del probador RA (cámara + ML Kit)

Diagramas semana 1:
- D1 Actividad reserva
- D2 Actividad compra digital
- D3 Actividad reposición
- D5 CU Iteración 2
- D9 Paquetes
- D15 Clases de análisis It.1
- D19 Despliegue

### Conteo semana 1
| | Ariany | Compañero |
|---|---|---|
| Pantallas | 10 | 4 |
| Diagramas | 3 | 7 |
| **Total semana 1** | **13** | **11** |


---

## REGLAS PARA NO CHOCAR

1. Ariany SOLO toca: backend/ + web/ + docs/ (sus diagramas)
2. Compañero SOLO toca: mobile/ + docs/ (sus diagramas)
3. Nunca commitear a main. Rama feature/ → PR → merge.
4. git pull origin main antes de empezar cada día.
5. Si necesitás tocar algo del otro → mensaje primero.