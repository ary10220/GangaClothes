# Delivery (CU29) — contrato de la API para la app móvil

Documento para **Integrante 2**: todo lo que hace falta para armar las pantallas
de delivery en Flutter sin esperar nada del backend. El backend ya está
terminado, desplegado y probado; las pantallas web equivalentes ya existen y se
pueden mirar como referencia visual.

> El contrato vivo está en **`/docs`** (OpenAPI) del servidor, bajo el grupo
> *9b. Envios a domicilio (CU29)*. Este archivo es el resumen con las reglas de
> negocio que el OpenAPI no cuenta.

---

## 1. Qué es un envío

Una compra en línea (canal `web` o `movil`) se entrega de dos formas:

| `venta.tipo_entrega` | Qué significa | Hay fila en `envio` |
|---|---|---|
| `sucursal` | el cliente la retira en la tienda (es el valor por defecto) | no |
| `delivery` | se la llevamos a su domicilio | sí, una |

El **costo del envío forma parte del total de la venta**:

```
venta.total = venta.subtotal − venta.descuento + venta.costo_envio
```

Eso significa que `POST /api/pagos` cobra `venta.total` como siempre: la app no
tiene que sumar nada. Si la app no implementa delivery, `tipo_entrega` queda en
`sucursal`, `costo_envio` en 0 y **nada cambia** respecto de lo que ya tiene.

Estados de un envío:

```
pendiente ──asignar──▶ asignado ──en-camino──▶ en_camino ──entregar──▶ entregado
     │                     │                        │
     └─────────────────────┴────────────────────────┴──▶ cancelado
```

El cliente **no** mueve estados: sólo consulta. Los mueve el encargado desde el
panel web (y desde la API, con permiso `envios:editar`).

---

## 2. Endpoints que consume la app

Todos bajo `/api/envios`. Salvo `GET /tarifa`, todos piden el `Authorization:
Bearer <token>` que la app ya manda.

### 2.1 `GET /api/envios/tarifa` — pública

Las reglas del cobro, para poder mostrarlas en pantalla («envío gratis desde
Bs 500»). No necesita sesión.

```json
{ "costo_base": 12.0, "costo_por_km": 3.5, "recargo_express_porcentaje": 45.0,
  "envio_gratis_desde": 500.0, "cobertura_km": 25.0,
  "minutos_preparacion": 45, "minutos_preparacion_express": 15, "velocidad_kmh": 18.0 }
```

### 2.2 `POST /api/envios/cotizar` — cuánto sale, **sin crear nada**

Es la que se llama cada vez que el cliente mueve el marcador en el mapa. No
escribe en la base: se puede llamar todas las veces que haga falta.

```jsonc
// petición
{ "latitud": -17.7672, "longitud": -63.1897,
  "sucursal_id": 1,          // opcional: por defecto, la del carrito del cliente
  "monto_compra": 250.0,     // opcional: por defecto, el total del carrito
  "express": false }
```

```jsonc
// respuesta 200
{
  "distancia_km": 1.97,
  "express": false,
  "dentro_de_cobertura": true,
  "cobertura_km": 25.0,
  "desglose": [                                   // ← mostrar RENGLÓN POR RENGLÓN
    { "concepto": "Costo base del envio",
      "detalle": "tarifa fija por salir a repartir", "importe": 12.0 },
    { "concepto": "Distancia hasta tu direccion",
      "detalle": "1,97 km x Bs 3,50 por km", "importe": 6.9 }
  ],
  "costo_envio": 18.9,
  "gratis": false,
  "falta_para_envio_gratis": 250.0,
  "envio_gratis_desde": 500.0,
  "minutos_estimados": 52,
  "entrega_estimada": "2026-09-20T04:15:42Z",
  "monto_compra": 250.0,
  "total_a_pagar": 268.9,
  "mensaje_cobertura": null,                       // texto listo cuando queda lejos
  "sucursal": { "id": 1, "nombre": "Sucursal Central", "direccion": "...",
                "ciudad": "Santa Cruz de la Sierra",
                "latitud": -17.7834, "longitud": -63.1821 },
  "destino": { "latitud": -17.7672, "longitud": -63.1897 },
  "tarifa": { ... }                                // lo mismo que GET /tarifa
}
```

**Importante:** el `desglose` se muestra completo, no sólo `costo_envio`. Es un
requisito del enunciado: el cliente tiene que ver de dónde sale cada boliviano
antes de confirmar. Un importe **negativo** en el desglose es una bonificación
(el envío gratis por monto) y conviene pintarlo en verde.

Si `dentro_de_cobertura` es `false`, `mensaje_cobertura` trae el texto ya
redactado para mostrar, y **no hay que dejar confirmar**.

### 2.3 `POST /api/envios` — pedir la entrega a domicilio

Se llama **antes de pagar**, con la venta en `carrito` o `pendiente`.

```jsonc
{ "venta_id": 88,
  "direccion": "Av. Alemana #1450, 3er anillo",   // 5 a 200 caracteres
  "referencia": "Edificio de ladrillo, timbre 3", // opcional
  "telefono_contacto": "70099887",                // 6 a 20 caracteres
  "latitud": -17.7935, "longitud": -63.1734,
  "express": false }
```

Devuelve `201` con `{ envio, cotizacion, venta }`. La `venta` viene **ya
recalculada**: su `total` incluye el envío, y es el monto que después hay que
pagar. Es idempotente: si la pasarela rechaza el pago y el cliente reintenta,
esta misma llamada actualiza el envío que ya existía con una cotización fresca.

Errores que hay que contemplar:

| Código | Cuándo |
|---|---|
| `400` | destino fuera de la zona de cobertura (el mensaje lo explica) |
| `400` | la compra ya está pagada, o el carrito está vacío |
| `400` | la sucursal de despacho no tiene coordenadas cargadas |
| `403` | la venta es de otro cliente |

### 2.4 `DELETE /api/envios/{id}` — volver a retiro en sucursal

Sólo antes de pagar. Devuelve la venta recalculada, ya sin el costo del envío.

### 2.5 `GET /api/envios/mios` — seguimiento del cliente

Lista los envíos de las compras **pagadas** del cliente, del más nuevo al más
viejo. Un delivery a medio armar en un carrito todavía no es un pedido y no
aparece acá.

```jsonc
[{
  "id": 4, "estado": "en_camino", "etiqueta_estado": "En camino", "activo": true,
  "direccion": "Av. Alemana #1450, 3er anillo",
  "latitud": -17.7935, "longitud": -63.1734,
  "referencia": "Edificio de ladrillo, timbre 3",
  "telefono_contacto": "70099887",
  "distancia_km": 1.45, "costo_envio": 17.08, "express": false,
  "repartidor": "Fabiola Aguilera", "motivo_cancelacion": null,
  "fecha_creacion": "2026-09-20T03:00:42Z",   // ← con estas cinco fechas
  "fecha_asignacion": "2026-09-20T03:10:00Z", //   se arma la línea de tiempo
  "fecha_salida": "2026-09-20T03:25:00Z",
  "fecha_estimada": "2026-09-20T04:15:42Z",
  "fecha_entrega": null,
  "sucursal": { "id": 1, "nombre": "Sucursal Central", "direccion": "...",
                "telefono": null, "ciudad": "Santa Cruz de la Sierra",
                "latitud": -17.7834, "longitud": -63.1821 },
  "cliente": { "id": 1, "nombre": "Sofia Rojas", "email": "...", "telefono": null },
  "venta": { "id": 88, "estado": "pagada", "canal": "web",
             "fecha": "...", "nro_comprobante": "C-000088",
             "subtotal": 219.9, "descuento": 0.0, "costo_envio": 17.08, "total": 236.98 },
  "prendas": [{ "id": 161, "sku": "P14-T1-C2", "prenda": "Camisa blanca formal",
                "talla": "S", "color": "Blanco", "cantidad": 1 }]
}]
```

`GET /api/envios/{id}` devuelve uno solo (el cliente, sólo los suyos).

Todas las fechas son **UTC marcadas con `Z`**, como el resto del sistema:
convertirlas a la hora del dispositivo antes de mostrarlas.

### 2.6 Endpoints del personal (no los usa la app del cliente)

Por si el compañero arma además una vista para el encargado:

```
GET  /api/envios?sucursal_id=&estado=     envios:ver
POST /api/envios/{id}/asignar   {repartidor}   envios:editar
POST /api/envios/{id}/en-camino                envios:editar
POST /api/envios/{id}/entregar                 envios:editar
POST /api/envios/{id}/cancelar  {motivo?}      envios:editar
```

---

## 3. Flujo completo de la compra con delivery

```
1. POST /api/ventas/carrito/items     (como ya lo hace hoy)
2. POST /api/envios/cotizar           cada vez que se mueve el marcador
3. POST /api/envios                   al elegir la dirección  →  devuelve la venta
4. POST /api/ventas/carrito/confirmar la venta pasa a "pendiente"
5. POST /api/pagos                    monto = venta.total (envío incluido)
6. GET  /api/envios/mios              seguimiento
```

Los pasos 3 y 4 son intercambiables: `POST /api/envios` acepta la venta en
`carrito` y en `pendiente`. La web hace 3 → 4 → 5.

El **inventario se descuenta al pagarse**, no al entregarse: no cambia respecto
de lo que la app ya hace.

---

## 4. El mapa en Flutter

Usar **[`flutter_map`](https://pub.dev/packages/flutter_map)**, que es Leaflet
para Flutter y consume los mismos tiles de OpenStreetMap que usa la web: es
gratis, no pide clave ni tarjeta.

```yaml
# pubspec.yaml
dependencies:
  flutter_map: ^7.0.2
  latlong2: ^0.9.1          # el tipo LatLng que usa flutter_map
  geolocator: ^13.0.1       # opcional: botón "usar mi ubicación"
```

```dart
FlutterMap(
  options: MapOptions(
    initialCenter: const LatLng(-17.7833, -63.1821),   // Santa Cruz
    initialZoom: 13,
    // El cliente marca su ubicación tocando el mapa.
    onTap: (tapPosition, punto) => cotizar(punto.latitude, punto.longitude),
  ),
  children: [
    TileLayer(
      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      userAgentPackageName: 'com.gangaclothes.app',
    ),
    MarkerLayer(markers: [
      Marker(point: origen, child: const Icon(Icons.store)),       // la sucursal
      if (destino != null)
        Marker(point: destino!, child: const Icon(Icons.place)),   // el destino
    ]),
    if (destino != null)
      PolylineLayer(polylines: [
        Polyline(points: [origen, destino!], strokeWidth: 3, color: Colors.pink),
      ]),
    // OpenStreetMap EXIGE mostrar su atribución.
    RichAttributionWidget(attributions: [
      TextSourceAttribution('OpenStreetMap contributors',
        onTap: () => launchUrl(Uri.parse('https://openstreetmap.org/copyright'))),
    ]),
  ],
)
```

> **La atribución de OpenStreetMap no es opcional**: es la condición de su
> licencia y es lo que permite usar los tiles sin pagar. La web la muestra en el
> pie del mapa; la app tiene que hacer lo mismo.

Para permisos de ubicación en Android, agregar a
`android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
```

---

## 5. Pantallas sugeridas

| Pantalla | Qué muestra | Endpoints |
|---|---|---|
| **Checkout** | elegir retiro / delivery, mapa para marcar, formulario (dirección, referencia, teléfono, express) y el **desglose del costo** | `cotizar`, `POST /api/envios` |
| **Mis pedidos** | lista de envíos con estado, mapa origen→destino y línea de tiempo | `GET /api/envios/mios` |

La línea de tiempo se arma con las cinco fechas del envío: *Compra confirmada*
(`fecha_creacion`), *Repartidor asignado* (`fecha_asignacion`), *En camino*
(`fecha_salida`), *Entregado* (`fecha_entrega`), y `fecha_estimada` para
prometer cuándo llega. Un envío `cancelado` corta la línea y muestra
`motivo_cancelacion`.

---

## 6. Cómo calcula el costo el backend

Está en `backend/app/modules/envios/tarifa.py` y es la **única** fuente del
precio: la app no replica ninguna cuenta, sólo muestra lo que devuelve
`cotizar`. Las reglas, por si hay que explicarlas en la defensa:

1. **Base fija** — Bs 12,00 por salir a repartir.
2. **Por kilómetro** — Bs 3,50 × la distancia hasta el destino.
3. **Express** — +45% sobre (1 + 2), y se prepara en 15 minutos en vez de 45.
4. **Envío gratis** — desde Bs 500,00 de compra lo absorbe la tienda.
5. **Cobertura** — más de 25 km desde la sucursal no se reparte.

La distancia sale de la **fórmula de Haversine** entre las coordenadas de la
sucursal y las del destino: es la distancia en línea recta sobre la superficie
de la Tierra, no el recorrido por calle. Por eso el tiempo estimado usa una
velocidad conservadora (18 km/h), que ya descuenta que el camino real es más
largo que la recta.

---

## 7. Datos para probar

El seed (`python seed.py`) deja:

- las **3 sucursales con coordenadas reales** (Central y Norte en Santa Cruz,
  Cochabamba);
- **3 envíos de demostración** en estados distintos (`entregado`, `en_camino`,
  `pendiente`), uno de ellos express, repartidos entre las tres cuentas de
  cliente del seed.

Con `sofia@gangaclothes.com / Cliente#2026` ya hay un envío entregado para ver
la línea de tiempo completa.

Coordenadas útiles de Santa Cruz para probar a mano:

| Lugar | Latitud | Longitud | Distancia desde Central |
|---|---|---|---|
| Equipetrol | -17.7672 | -63.1897 | ~2 km |
| Barrio Urbarí | -17.7965 | -63.1870 | ~1,5 km |
| Plan 3000 | -17.8258 | -63.1094 | ~9 km |
| Cochabamba | -17.3868 | -66.1586 | ~319 km (fuera de cobertura) |
