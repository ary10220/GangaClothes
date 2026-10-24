# Auditoría del probador virtual (CU22) — ¿migrar a 3D?

Fecha: 26/09/2026 · Rama `main` (`08ec8bc`) · Flutter 3.47.1 stable

> **Alcance y límites de esta auditoría.** Se leyó todo el código del probador
> (`mobile/lib/features/virtual_fitting/`, 1542 líneas), el modelo y la API de
> `asset_ar` en el backend, el formulario de la web y los tests. **No había
> ningún teléfono conectado por adb**, así que **no hay mediciones reales de FPS
> ni capturas de pantalla**. Los números de rendimiento de la sección 1.5 salen
> del código (límites fijos) y de la documentación de ML Kit. Son estimaciones y
> están marcadas como tales. Al final (sección 1.6) va el procedimiento para
> medir en el Redmi 15C antes de decidir.

---

## 1. Estado actual

### 1.1 Paquetes y versiones (según `pubspec.lock`)

| Paquete | Versión | Uso |
|---|---|---|
| `camera` | 0.12.1 | Preview y stream de frames |
| `camera_android_camerax` | 0.7.4+8 (transitivo) | Implementación en Android |
| `google_mlkit_pose_detection` | 0.16.1 | Pose (33 landmarks) |
| `google_mlkit_commons` | 0.13.0 (transitivo) | `InputImage` |

El render de la prenda no usa ningún paquete: es un `CustomPainter` de Flutter
([garment_painter.dart](../mobile/lib/features/virtual_fitting/garment_painter.dart)).

### 1.2 Pipeline

```
CameraController (frontal, ResolutionPreset.medium, NV21)
  └─ startImageStream ──► _processCameraImage          virtual_fitting_sheet.dart:279
        · descarta el frame si hay otro en proceso (_processingFrame)
        · descarta el frame si pasaron < 120 ms desde el último   :282-285
        · InputImage.fromBytes (NV21, 1 plano) con la rotación del sensor
        └─ PoseDetector(mode: stream, model: base)             :199-204
              └─ BodyPose.fromLandmarks (normaliza 0..1, espeja, estima lo que falta)
                    └─ BodyTracker.update (EMA 50 %) ──► setState
                          └─ GarmentPainter.paint (Stack: CameraPreview + CustomPaint)
```

- La cámara se muestra con `CameraPreview` dentro de un `FittedBox(cover)`, y
  `PreviewMapper` replica esa misma transformación para llevar los landmarks a
  píxeles de pantalla ([garment_painter.dart:10-35](../mobile/lib/features/virtual_fitting/garment_painter.dart#L10-L35)).
- La prenda es el último `asset_ar` con `tipo = png_overlay` de la variante. Si
  no hay ninguno, se usa la foto del producto. Si esta tampoco carga, se dibuja
  una silueta vectorial del color de la variante
  ([catalog_models.dart:77](../mobile/lib/features/catalog/catalog_models.dart#L77)).

### 1.3 Landmarks que se usan

- **Solo 2D.** Del `PoseLandmark` se leen `x`, `y` y `likelihood`, y **`z` se
  descarta** ([virtual_fitting_sheet.dart:322-329](../mobile/lib/features/virtual_fitting/virtual_fitting_sheet.dart#L322-L329)).
- **Aclaración importante: ML Kit Pose no tiene "world landmarks".** Esos son de
  MediaPipe Pose Landmarker (coordenadas en metros con origen en la cadera). En
  ML Kit, `z` está en **píxeles de imagen**, con el origen aproximadamente en el
  centro de las caderas. Los valores negativos van hacia la cámara, y Google lo
  describe como un valor *experimental*, no una coordenada 3D real. Sirve para
  una estimación gruesa de giro. No sirve para una reconstrucción 3D fiable.
- Articulaciones que influyen en la prenda: **hombros** (obligatorios, con
  likelihood ≥ 0.5 y dentro del frame con un margen de 10 %), **caderas**,
  **codos** y **muñecas**. Cara, manos, rodillas y pies solo se dibujan con
  "Ver puntos".
- Si una cadera, un codo o una muñeca tiene likelihood < 0.5, **se inventa**
  desde la línea de hombros. La cadera queda a 1.3× el ancho de hombros hacia
  abajo, y el codo y la muñeca en posición de reposo
  ([body_model.dart:127-163](../mobile/lib/features/virtual_fitting/body_model.dart#L127-L163)).

### 1.4 Cómo se escala y posiciona el PNG

**Partes de arriba y vestidos** (`_paintImage`, [garment_painter.dart:163](../mobile/lib/features/virtual_fitting/garment_painter.dart#L163)):

- **Escala única = ancho de hombros en pantalla.** Se supone que en el PNG los
  hombros caen en x = 25 % y 75 % del ancho: `s = anchoHombros × escala / (0.5 × anchoPNG)`.
  El `escala` del `asset_ar` multiplica ese valor.
- **Vertical:** `measureShoulderLine` busca en el canal alfa la primera fila del
  40 % superior cuyo ancho supera el 60 % del máximo, y le suma 3 %. Esa fila se
  alinea con el punto medio de los hombros.
- **Rotación:** la inclinación de la línea de hombros (roll), normalizada a
  (−90°, 90°) para que la prenda nunca quede al revés.
- **Mangas:** las franjas laterales del PNG (25 % de ancho cada una, toda la
  altura) se recortan y rotan alrededor del hombro según el ángulo hombro→codo
  respecto de un reposo de ±17°. Hay una zona muerta de ±15° (0.26 rad). En
  manga larga, la franja se parte al 45 % de la altura y el antebrazo rota por
  separado desde el codo. El largo de manga se deduce **por el nombre** del
  producto (`sleeveModeFor`).
- `torsoLength` se calcula pero **no se usa** para escalar: el alto de la
  prenda sale solo del ancho de hombros.

**Pantalones y faldas** (`_paintOnHips`, [garment_painter.dart:148](../mobile/lib/features/virtual_fitting/garment_painter.dart#L148)):
se anclan al punto medio de las caderas. El ancho es `max(anchoCadera, 0.7 × anchoHombros) × 1.35`,
la rotación es la inclinación de la cadera y la cintura va un 18 % por encima de
la articulación. El tipo de anclaje también se deduce por el nombre (`anchorFor`).

### 1.5 Rendimiento (estimado; **no medido**)

| Métrica | Valor | Fuente |
|---|---|---|
| Preview de cámara | ~30 fps, independiente de la pose (textura nativa) | CameraX |
| Resolución analizada | 640×480 (`ResolutionPreset.medium`) | código |
| Techo de inferencias | **≤ 8.3/s** (una cada ≥ 120 ms) | `virtual_fitting_sheet.dart:282` |
| Latencia de ML Kit *base* | ~33 ms en Pixel 4 (≈ 30 fps, dato de Google) | docs de ML Kit |
| Latencia esperable en Redmi 15C | ~50–100 ms (gama baja): **sin medir** | estimación |
| Frecuencia real de la prenda | **~5–8 Hz** | techo de 120 ms + inferencia |
| Frames de cámara descartados | **~70–80 % a propósito** (throttle + `_processingFrame`) | diseño |
| Retardo visual | ~1 inferencia + EMA 50 % ≈ **150–300 ms** | cálculo |

Conclusiones de la tabla:

- El cuello de botella no es la GPU: es que **la prenda solo se repinta cuando
  llega una pose nueva**. El video corre a 30 fps y la prenda avanza "a
  saltitos" a unos 5–8 Hz, sin interpolar entre poses.
- Pintar la prenda es barato (2–5 `drawImage` por frame). `measureShoulderLine`
  corre una sola vez por imagen. No hay razones de código para esperar jank en
  el hilo de UI.

### 1.6 Cómo medirlo en el teléfono (pendiente)

1. `flutter run --profile` con el Redmi conectado y DevTools → *Performance*:
   la pestaña de frames da el FPS de UI/raster y los frames perdidos.
2. Latencia de inferencia: agregar **temporalmente** (sin commitear) un
   `Stopwatch` alrededor de `detector.processImage` en
   `virtual_fitting_sheet.dart:312` y hacer `debugPrint` del promedio cada 30
   poses. Para la frecuencia de pose, contar los `setState` por segundo.
3. Capturas de los casos de la sección 2 con `adb exec-out screencap -p > caso.png`
   o con la captura del propio teléfono, con "Ver puntos" encendido.

---

## 2. Cómo soporta el movimiento hoy

Análisis a partir del código. Hay que confirmar cada caso con una captura en el
teléfono.

| Situación | Qué pasa | Por qué (código) |
|---|---|---|
| **Frente a cámara, quieto** | Bien. Prenda estable y alineada a hombros. | Caso para el que está diseñado. |
| **Inclinarse de costado (roll)** | Bien. La prenda rota con la línea de hombros. | `angle` de `GarmentGeometry`. |
| **Girar el torso (yaw) 20–45°** | ⚠️ La prenda **se achica entera** (también a lo alto) y sigue vista de frente. No hay perspectiva. | La escala es solo el ancho de hombros proyectado; `z` se ignora. |
| **Girar de perfil (> 60°)** | ❌ La prenda se vuelve una tira angosta. Con hombros a < 4 % del frame, la pose se descarta y la prenda **queda congelada 1.2 s** en el último lugar. ML Kit además puede intercambiar izquierda/derecha. | `sw < .04` → `null` ([body_model.dart:115](../mobile/lib/features/virtual_fitting/body_model.dart#L115)); `lostAfter` 1200 ms. |
| **Acercarse / alejarse** | Bien mientras los hombros estén en cuadro: la escala sigue el ancho de hombros. | Escala proporcional. |
| **Muy cerca (hombros fuera de cuadro)** | ❌ Se pierde la pose y la prenda queda congelada 1.2 s. Luego desaparece. | `_inFrame` con margen de 10 %. |
| **Caderas fuera de cuadro** | ⚠️ Partes de arriba: sin efecto, porque la altura no depende de la cadera. **Pantalones**: se anclan a una cadera *inventada* a 1.3× el ancho de hombros. | Estimación en `fromLandmarks`. |
| **Levantar brazos (hasta ~90°)** | Bien. La manga rota con el brazo; la manga larga se dobla en el codo. | `_paintSleeve`. |
| **Brazos arriba de la cabeza** | ⚠️ La franja rota ~150°. Como la franja es todo el 25 % lateral del PNG, **se lleva un pedazo del costado del torso** y queda un hueco en la cintura. | Franja de altura completa. |
| **Brazos cruzados / mano delante del pecho** | ❌ **Sin oclusión**: la prenda tapa la mano y el antebrazo. | Siempre se pinta encima. |
| **Pelo largo / mentón** | ⚠️ El cuello del PNG puede tapar el mentón o el pelo que cae sobre los hombros. | Sin oclusión. |
| **Brazo con likelihood < 0.5** | ⚠️ La manga vuelve de golpe al reposo (el codo estimado está en reposo). Cuando reaparece, salta. | Estimación + zona muerta. |
| **Dos personas en cuadro** | ⚠️ ML Kit devuelve una sola pose y puede saltar de persona. | `poses.firstOrNull`. |
| **Botón "Espejo"** | ⚠️ Invierte las poses pero no el preview. Con el espejo apagado en la frontal, la prenda queda del lado contrario. Al cambiarlo, el EMA "desliza" la prenda de un lado al otro. | `_mirror` solo afecta a la pose. |

**Suavizado entre frames:** hay un EMA simple con α = 0.5 por pose
([body_model.dart:235](../mobile/lib/features/virtual_fitting/body_model.dart#L235)).
Quita parte del temblor, pero:

- es fijo: agrega retardo cuando la persona se mueve rápido y no alcanza para el
  ruido cuando está quieta;
- no interpola entre poses, así que la prenda "salta" a la frecuencia de
  inferencia (~5–8 Hz);
- no descarta outliers (un hombro mal detectado en un frame arrastra media
  prenda);
- el `likelihood` mezclado es el del frame nuevo, así que un punto estimado
  (likelihood 0) se mezcla igual con uno real.

**Tests existentes** ([body_model_test.dart](../mobile/test/body_model_test.dart)):
normalización y rotación, espejo, rechazo de hombros no confiables, estimación
de joints, EMA y olvido a los 1.2 s, manga que sigue al codo y ángulo que nunca
da la vuelta. No hay tests del painter ni de casos de giro.

---

## 3. Qué implicaría pasar a 3D (ML Kit + `.glb` sobre la cámara)

### 3.1 Motor de render 3D en Flutter (estado a septiembre 2026)

| | **Thermion** (ex flutter_filament) | **flutter_scene** | **flutter_unity_widget** |
|---|---|---|---|
| Última versión | 0.5.0 (hace ~5 semanas) | 0.23.0 (hace ~1 mes) | 2.0.2.1 (hace **~2 años** en pub.dev); Unity 6 solo vía rama/fork `flutter_unity_widget_2` |
| Mantenimiento | Activo, un mantenedor principal | Activo (autor del equipo de Flutter/Impeller) | El propio autor recomienda **no usarlo en proyectos nuevos** |
| Canal de Flutter | Stable, pero **exige `--enable-native-assets`**. La primera build baja binarios de Filament. | **Stable ≥ 3.47** (hasta hace poco exigía master). Depende de Flutter GPU, que sigue en *preview*. | Stable (≥ 3.0) |
| Motor | Filament 1.69 (PBR, glTF, skinning, animación) | Impeller / Flutter GPU (glTF/glb, skinning) | Unity completo |
| ¿Compone sobre `CameraPreview`? | Probable: renderiza a una `Texture` con fondo configurable. **Hay que probar el fondo transparente en Android.** | Probable y el más natural: dibuja dentro del árbol de Flutter. **Sin confirmar en docs.** | Sí, pero lo lógico sería que **Unity maneje la cámara** (AR Foundation). Mezclarlo con `CameraPreview` es frágil. |
| Estabilidad en Android | Media. Solo arm64, dependencia nativa pesada y pocos usuarios. | Media-baja. API en preview con cambios que rompen; Impeller en Android usa Vulkan, con GLES como respaldo en gama baja. | Media. Build en dos proyectos, APK +40–80 MB, problemas conocidos de ciclo de vida. |
| Encaje con este proyecto | Bueno si el spike funciona | **El mejor** si el spike funciona: ya estamos en 3.47.1 stable y no suma binarios nativos | Malo: reescribe el probador en C#/Unity y duplica el pipeline de pose |

**Recomendación si se hiciera:** `flutter_scene` como primera opción y Thermion
como plan B, **después de un spike de 1 día** en el Redmi. El spike tiene que
responder tres preguntas: (a) ¿compila y corre?, (b) ¿el fondo queda
transparente sobre la cámara?, (c) ¿cuántos FPS da con un `.glb` de ~20 k
triángulos? `flutter_unity_widget` queda descartado para el tiempo disponible.

### 3.2 Rotación del torso desde los landmarks

Como ML Kit no da world landmarks, hay dos fuentes y conviene combinarlas.

**a) Con `z` de ML Kit** (misma escala en píxeles que `x`):

```
L, R = hombro izq/der ;  Lh, Rh = cadera izq/der   (x, y, z en píxeles del frame)
yaw   = atan2(L.z - R.z, L.x - R.x)          // giro sobre el eje vertical
pitch = atan2(mid(Lh,Rh).z - mid(L,R).z,
              mid(Lh,Rh).y - mid(L,R).y)     // inclinación adelante/atrás
roll  = atan2(L.y - R.y, L.x - R.x)          // ya se calcula hoy
```

Con espejo se invierte el signo de `yaw`. El `z` de ML Kit es ruidoso, así que
va con un filtro fuerte.

**b) Por escorzo, sin `z`** (más estable). Se calibra en los primeros ~15 frames
de frente el cociente `k0 = anchoHombros / largoTorso`. Luego:

```
|yaw| = acos(clamp((anchoHombros / largoTorso) / k0, 0, 1))
signo  = signo(L.z - R.z)   // o: lado hacia el que se corre la nariz respecto del centro de hombros
```

Con `yaw`, `pitch` y `roll` se arma un cuaternión, se filtra con slerp o One
Euro y se aplica al nodo raíz del modelo. Para posición y escala conviene una
**cámara ortográfica** alineada con el preview: el modelo se ubica en
`shoulderMid` (coordenadas del `PreviewMapper`) y se escala por el ancho de
hombros dividido por `cos(yaw)`. Así no hace falta estimar la distancia real.

**El problema de fondo: los brazos.** Un `.glb` rígido gira con el torso, pero
las mangas **no siguen los brazos**. Hoy el 2D sí los sigue. Para igualarlo,
cada prenda tiene que estar **riggeada** (huesos hombro/codo con pesos de
skinning), y hay que manejar esos huesos desde los ángulos 2D de ML Kit con una
IK simple. Es el doble de trabajo por prenda y por código. Sin eso, la
migración a 3D es **una regresión visible** respecto de lo que ya se mostró.

### 3.3 Cambios en el backend (exactos)

El backend ya acepta `modelo_3d`: `tipo` es un `String(20)` libre y el
comentario del modelo ya lo lista. **La web ya ofrece `modelo_3d` en el
formulario** ([prendas.html:550](../web/src/app/features/admin/prendas/prendas.html#L550)).
Lo mínimo sería:

1. **Validar `tipo`**: en `AssetIn`
   ([router.py:84-87](../backend/app/modules/prendas/router.py#L84-L87)) pasar
   de `tipo: str` a `Literal["png_overlay", "modelo_3d"]`. Si se registra un
   `modelo_3d`, validar que `url_recurso` termine en `.glb` o `.gltf`.
2. **Textos**: el `summary` de `POST /variantes/{id}/asset-ar` (`router.py:210`)
   y de `GET /catalogo/variantes/{id}/asset-ar` (`router.py:241`) dicen "PNG".
   También hay que actualizar el comentario en `service.py` (~línea 365).
3. **Metadatos opcionales del modelo** (solo si se hace 3D de verdad). Agregar a
   `AssetAR` ([catalogo.py:82-88](../backend/app/models/catalogo.py#L82-L88))
   `offset_y` (dónde está la línea de hombros en el modelo) y `rig` (bool). Se
   agregan con el `ALTER TABLE` idempotente de `aplicar()` en
   `backend/app/core/migraciones.py`, igual que las otras columnas. Hay que exponerlos en
   `_recurso_ar` (`service.py:278`).
4. **Borrado de recursos**: hoy no hay `DELETE /asset-ar/{id}` y la app toma
   "el último por id". Para convivir con PNG y 3D conviene agregar el borrado,
   con bitácora como el POST.
5. **Hosting de `.glb`**: igual que los PNG, en `web/public/...` (Vercel sirve
   `model/gltf-binary`). Los `.glb` pesan de 1 a 10 MB, así que conviene
   comprimir con Draco o meshopt.

**No hace falta migrar datos.** Los 104 `png_overlay` se quedan y funcionan de
respaldo. En la app:

- agregar `ArResource.isModel3d` y `Variant.model3d` (el último `modelo_3d`);
- elegir 3D si existe y el motor inicializa, y si no, usar el PNG actual.

El test `catalog_widget_test.dart:344` ya incluye un `modelo_3d` que hoy se
ignora.

### 3.4 De dónde salen los `.glb`

Hay 16 prendas con foto. Los colores se resuelven cambiando el material, así
que no hace falta un modelo por cada una de las 104 variantes.

| Origen | Calidad / parecido con la prenda real | Trabajo por prenda | Costo |
|---|---|---|---|
| **Modelos libres** (Sketchfab CC-BY, Poly Pizza) | Genéricos: "una remera", no *esta* remera. Topología y escala dispares. | 1–2 h (buscar, limpiar, centrar, texturizar con la foto) | Gratis (atribución) |
| **Comprados** (CGTrader, TurboSquid) | Mejor topología, igual de genéricos. Pocos vienen riggeados. | 1–2 h | ~10–50 USD c/u |
| **Generados desde la foto** (Tripo, Meshy; open source: Hunyuan3D-2, TRELLIS) | Se parecen a la foto, pero salen como **malla rígida y "inflada"**, con la espalda inventada, sin rig y con topología sucia. | 0.5–1 h de generación y limpieza; **+2–4 h de rig** | Créditos gratis limitados o GPU local |
| **CLO3D / Marvelous Designer** (patrones) | La mejor: tela real, simulable y fiel. | 4–8 h aprendiendo, 2–4 h por prenda con experiencia | Licencia (hay educativa) |
| **Blender a mano** | Depende de la habilidad. | 4–10 h para alguien que recién empieza | Gratis |

A todo eso se suma, por prenda, el **rig para las mangas**: transferir pesos
desde un cuerpo de Mixamo o MakeHuman en Blender, unas **2–4 h**. En total, un
catálogo mínimo de 3–4 prendas "de demo" con rig lleva **1–2 semanas** de
trabajo de modelado, aparte del código.

---

## 4. Veredicto

> No encontré la fecha de entrega en el repo. El veredicto se da en días de
> trabajo; comparalo con el calendario real.

### 4.1 ¿Es realista la migración a 3D?

**No, para esta entrega.** El cálculo para llegar al nivel del 2D actual:

| Tarea | Días |
|---|---|
| Spike del motor en el Redmi | 1 |
| Integración: motor, cámara ortográfica y transformación desde la pose | 2–3 |
| Rotación con filtro | 1 |
| IK de brazos sobre el rig | 2–3 |
| Backend y admin | 0.5 |
| Modelos: 3–4 prendas riggeadas | 5–10 |
| Pruebas en teléfono | 1–2 |
| **Total** | **~13–20 días** |

Todo depende de un spike que puede fallar. Sin rig, el 3D se ve "más 3D" al
girar, pero **pierde el seguimiento de brazos** que el docente pidió
explícitamente y que ya se mostró.

**Si igual quieren algo de 3D para mostrar:** una sola prenda riggeada con
`flutter_scene`, detrás de un interruptor "Vista 3D (experimental)", con el PNG
como vista por defecto. Hacerlo solo si el spike del día 1 sale bien y después
de las mejoras 2D.

### 4.2 Qué se puede lograr mejorando el 2D (~3–5 días)

Ordenado por impacto sobre esfuerzo:

1. **Movimiento fluido (≈ 1 día).**
   - Repintar con un `Ticker` a 60 fps interpolando entre las dos últimas poses
     (o extrapolando con la velocidad), en vez de repintar solo en cada pose.
   - Cambiar el EMA fijo por un **filtro One Euro** por joint: sin temblor
     cuando la persona está quieta y con poco retardo cuando se mueve.
   - Bajar el throttle de 120 ms a uno adaptativo (p. ej. 1.2× la latencia
     medida).
   - Rechazar saltos imposibles de un frame.

   Es lo que más se nota a simple vista: la prenda deja de "saltar".
2. **Giro por perspectiva (≈ 1–1.5 días).**
   - Estimar `yaw` (sección 3.2) y dibujar el PNG con
     `canvas.transform(Matrix4.identity()..setEntry(3, 2, 0.0015)..rotateY(yaw))`.
     Un `Matrix4` con perspectiva en `Canvas` da un plano girado en 3D real,
     sin motor.
   - Escalar **ancho por hombros y alto por largo de torso**, para que al girar
     no se achique la prenda entera.
   - Con más de ~55°, bajar la opacidad y mostrar "gira hacia la cámara".

   Convence hasta unos ±40°.
3. **Oclusión barata (≈ 1 día).**
   - Cuando la muñeca o el codo caen dentro del polígono del torso **y** su `z`
     es menor que el de los hombros (brazo por delante), recortar la prenda con
     `canvas.clipPath` (`PathOperation.difference`) usando una cápsula
     antebrazo + mano. Así se ve la cámara a través.
   - Hacer lo mismo con un óvalo en mentón y cuello (desde nariz, orejas y
     boca).

   Alternativa más cara: `google_mlkit_selfie_segmentation` sirve para el borde
   de la silueta, pero no distingue mano de torso.
4. **Robustez (≈ 0.5 día).**
   - Desvanecer la prenda según el likelihood en vez de congelarla 1.2 s.
   - No inventar el codo en reposo si hace < 300 ms que se vio (mantener el
     último real).
   - Limitar la franja de manga a la zona de la manga para no arrancar el
     costado del torso con los brazos arriba.
   - Arreglar el botón Espejo (o quitarlo).
5. **Opcional: vista lateral.** Una segunda imagen `png_overlay` por variante
   para el perfil, con crossfade según `yaw`. Requiere un campo `vista` en
   `asset_ar` y fotos de perfil, que hoy no existen.

### 4.3 Riesgos concretos

| Camino | Riesgos |
|---|---|
| **3D** | El spike falla: fondo no transparente sobre la cámara, crash de Impeller/Vulkan en el Redmi o native assets que no compilan en Windows. Días perdidos sin nada mostrable. · Los modelos son el cuello de botella real y no se paraleliza con código. · Sin rig se pierde el seguimiento de brazos (regresión frente al docente). · APK más pesado y más calor/batería en gama baja. · `flutter_scene` y Flutter GPU están en preview: un `pub upgrade` puede romper la build. · Tocar el vestidor rompe la regla de "PNG recortado a la silueta" y el flujo de `asset_ar` ya registrado en prod si se hace sin respaldo. |
| **Mejorar 2D** | La perspectiva de un plano se nota "cartón" más allá de ~45°: hay que limitarla y comunicarlo. · El `z` de ML Kit es experimental; la oclusión por `z` puede fallar y conviene combinarla con la condición geométrica. · Más cálculo por frame con el Ticker a 60 fps (bajo, pero hay que medirlo en el Redmi). · Riesgo bajo de regresión si se sigue el flujo habitual: checkpoint y tag antes, tests de `body_model` ampliados y prueba en teléfono. |

**Recomendación:** mejorar el 2D (4.2 puntos 1–4) y medir en el Redmi antes y
después con el procedimiento de 1.6, para tener números concretos en la
defensa. El 3D queda como trabajo futuro documentado en esta auditoría, o como
demo de una sola prenda si sobra tiempo y el spike funciona.

---

### Fuentes

- ML Kit Pose Detection: significado de `z` y rendimiento del SDK base — https://developers.google.com/ml-kit/vision/pose-detection
- thermion_flutter 0.5.0 — https://pub.dev/packages/thermion_flutter · https://thermion.dev/
- flutter_scene 0.23.0 — https://pub.dev/packages/flutter_scene · changelog: https://pub.dev/packages/flutter_scene/changelog
- flutter_unity_widget — https://pub.dev/packages/flutter_unity_widget · soporte Unity 6: https://github.com/juicycleff/flutter-unity-view-widget/issues/967
