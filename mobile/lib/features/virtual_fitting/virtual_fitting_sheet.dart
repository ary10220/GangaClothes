import 'dart:async';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';

import '../../shared/widgets/gc_button.dart';
import '../catalog/catalog_models.dart';
import 'body_model.dart';
import 'garment_painter.dart';

typedef CameraEnumerator = Future<List<CameraDescription>> Function();

class VirtualFittingSheet extends StatefulWidget {
  const VirtualFittingSheet({
    required this.productName,
    required this.variant,
    required this.imageUrl,
    this.overlayUrl,
    this.overlayScale = 1,
    this.cameraEnumerator,
    super.key,
  });

  final String productName;
  final Variant variant;

  /// Foto de la prenda; se usa si no hay PNG del probador o si este falla.
  final String imageUrl;

  /// PNG con fondo transparente registrado como recurso AR de la variante.
  final String? overlayUrl;
  final double overlayScale;
  final CameraEnumerator? cameraEnumerator;

  @override
  State<VirtualFittingSheet> createState() => _VirtualFittingSheetState();
}

class _VirtualFittingSheetState extends State<VirtualFittingSheet>
    with WidgetsBindingObserver {
  static const _initTimeout = Duration(seconds: 12);
  static const _maxRetries = 3;
  static final _jointByName = {for (final j in BodyJoint.values) j.name: j};

  CameraController? _camera;
  PoseDetector? _poseDetector;
  final _tracker = BodyTracker();
  String? _error;
  bool _loading = true;
  bool _initializing = false;
  bool _processingFrame = false;
  DateTime? _lastProcessedAt;
  int _cameraGeneration = 0;
  int _retries = 0;
  bool _showPoints = false;
  bool _mirror = true;
  bool _loggedFrame = false;

  ui.Image? _garment;
  bool _garmentIsOverlay = false;
  bool _garmentFailed = false;
  ImageStream? _garmentStream;
  ImageStreamListener? _garmentListener;
  late final List<String> _garmentCandidates;
  int _garmentIndex = 0;

  bool get _mobilePlatform =>
      defaultTargetPlatform == TargetPlatform.android ||
      defaultTargetPlatform == TargetPlatform.iOS;

  SleeveMode get _sleeves => sleeveModeFor(widget.productName);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final overlay = widget.overlayUrl?.trim();
    _garmentCandidates = [
      if (overlay != null && overlay.isNotEmpty) overlay,
      if (widget.imageUrl.trim().isNotEmpty) widget.imageUrl.trim(),
    ];
    if (_garmentCandidates.isEmpty) {
      _loading = false;
      _error = 'No hay una imagen disponible para esta prenda.';
    } else if (!_mobilePlatform && widget.cameraEnumerator == null) {
      _loading = false;
      _error = 'El vestidor virtual solo está disponible en Android y iOS.';
    } else {
      _loadGarment();
      unawaited(_initializeCamera());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _garmentStream?.removeListener(_garmentListener!);
    unawaited(_disposeCamera());
    super.dispose();
  }

  // `inactive` llega con el diálogo de permiso, la barra de notificaciones o
  // cualquier ventana del sistema: ahí la cámara se queda como está. Solo se
  // libera cuando la app realmente pasa a segundo plano.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      if (_camera == null && !_initializing && _error == null) {
        _retries = 0;
        unawaited(_initializeCamera());
      }
    } else if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.detached) {
      unawaited(_disposeCamera());
    }
  }

  // ------------------------------------------------------------- imagen

  void _loadGarment() {
    if (_garmentIndex >= _garmentCandidates.length) {
      if (mounted) setState(() => _garmentFailed = true);
      return;
    }
    final url = _garmentCandidates[_garmentIndex];
    final isOverlay = url == widget.overlayUrl?.trim();
    final stream = NetworkImage(url).resolve(ImageConfiguration.empty);
    final listener = ImageStreamListener(
      (info, _) {
        if (!mounted) return;
        setState(() {
          _garment = info.image;
          _garmentIsOverlay = isOverlay;
          _garmentFailed = false;
        });
      },
      onError: (error, _) {
        debugPrint('[POSE] No se pudo cargar la prenda $url: $error');
        if (!mounted) return;
        _garmentIndex++;
        _loadGarment();
      },
    );
    _garmentStream?.removeListener(_garmentListener!);
    _garmentStream = stream;
    _garmentListener = listener;
    stream.addListener(listener);
  }

  // ------------------------------------------------------------- cámara

  Future<void> _initializeCamera() async {
    if (_initializing ||
        (!_mobilePlatform && widget.cameraEnumerator == null)) {
      return;
    }
    _initializing = true;
    final generation = ++_cameraGeneration;
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    CameraController? camera;
    PoseDetector? detector;
    try {
      final cameras = await (widget.cameraEnumerator ?? availableCameras)();
      if (!mounted || generation != _cameraGeneration) return;
      if (cameras.isEmpty) throw StateError('No camera available');
      final description = cameras.firstWhere(
        (item) => item.lensDirection == CameraLensDirection.front,
        orElse: () => cameras.first,
      );
      _mirror = description.lensDirection == CameraLensDirection.front;
      camera = CameraController(
        description,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: defaultTargetPlatform == TargetPlatform.android
            ? ImageFormatGroup.nv21
            : ImageFormatGroup.bgra8888,
      );
      await camera.initialize().timeout(_initTimeout);
      if (!mounted || generation != _cameraGeneration) {
        await camera.dispose();
        return;
      }
      detector = PoseDetector(
        options: PoseDetectorOptions(
          mode: PoseDetectionMode.stream,
          model: PoseDetectionModel.base,
        ),
      );
      _camera = camera;
      _poseDetector = detector;
      await camera.startImageStream(_processCameraImage);
      if (!mounted || generation != _cameraGeneration) {
        if (identical(_camera, camera)) _camera = null;
        if (identical(_poseDetector, detector)) _poseDetector = null;
        await camera.dispose();
        await detector.close();
        return;
      }
      camera = null;
      detector = null;
      _retries = 0;
      setState(() => _loading = false);
    } catch (caught) {
      await detector?.close();
      await camera?.dispose();
      if (!mounted || generation != _cameraGeneration) return;
      _camera = null;
      _poseDetector = null;
      setState(() {
        _loading = false;
        _error = _cameraError(caught);
      });
    } finally {
      _initializing = false;
      if (mounted && _camera == null && _error == null) {
        // La inicialización fue invalidada (p. ej. por un `paused` mientras
        // se pedía el permiso). Si la app está en primer plano, se reintenta.
        final lifecycle = WidgetsBinding.instance.lifecycleState;
        final foreground =
            lifecycle == null || lifecycle == AppLifecycleState.resumed;
        if (foreground && _retries < _maxRetries) {
          _retries++;
          unawaited(
            Future<void>.delayed(
              const Duration(milliseconds: 250),
              _initializeCamera,
            ),
          );
        } else if (_loading) {
          setState(() => _loading = false);
        }
      }
    }
  }

  Future<void> _disposeCamera() async {
    _cameraGeneration++;
    final camera = _camera;
    final detector = _poseDetector;
    _camera = null;
    _poseDetector = null;
    _tracker.clear();
    _processingFrame = false;
    if (camera != null) {
      try {
        if (camera.value.isStreamingImages) await camera.stopImageStream();
      } catch (_) {
        // The controller may already be releasing its native stream.
      }
      await camera.dispose();
    }
    await detector?.close();
  }

  void _retry() {
    _retries = 0;
    _error = null;
    unawaited(_initializeCamera());
  }

  // ------------------------------------------------------------- frames

  Future<void> _processCameraImage(CameraImage image) async {
    if (_processingFrame || _poseDetector == null || _camera == null) return;
    final now = DateTime.now();
    if (_lastProcessedAt != null &&
        now.difference(_lastProcessedAt!) < const Duration(milliseconds: 120)) {
      return;
    }
    final camera = _camera!;
    final rotation = _rotationFor(camera.description);
    if (rotation == null) return;
    final inputImage = _inputImageFromCameraImage(image, rotation);
    if (inputImage == null) {
      debugPrint(
        '[POSE] Frame descartado: no se pudo crear InputImage. '
        'format=${InputImageFormatValue.fromRawValue(image.format.raw)} '
        'planes=${image.planes.length} size=${image.width}x${image.height}',
      );
      return;
    }
    if (!_loggedFrame) {
      _loggedFrame = true;
      debugPrint(
        '[POSE] frame=${image.width}x${image.height} rotation=$rotation '
        'preview=${camera.value.previewSize} '
        'sensor=${camera.description.sensorOrientation} mirror=$_mirror',
      );
    }

    _processingFrame = true;
    _lastProcessedAt = now;
    final generation = _cameraGeneration;
    final detector = _poseDetector!;
    try {
      final poses = await detector.processImage(inputImage);
      if (!mounted ||
          generation != _cameraGeneration ||
          detector != _poseDetector) {
        return;
      }
      final pose = poses.firstOrNull;
      final body = pose == null
          ? null
          : BodyPose.fromLandmarks(
              raw: {
                for (final landmark in pose.landmarks.values)
                  if (_jointByName[landmark.type.name] != null)
                    _jointByName[landmark.type.name]!: BodyPoint(
                      landmark.x,
                      landmark.y,
                      landmark.likelihood,
                    ),
              },
              imageWidth: image.width,
              imageHeight: image.height,
              rotationDegrees: _degrees(rotation),
              mirror: _mirror,
            );
      if (_tracker.update(body) && mounted) setState(() {});
    } catch (error, stackTrace) {
      debugPrint('[POSE] Error procesando frame: $error');
      debugPrintStack(stackTrace: stackTrace);
    } finally {
      _processingFrame = false;
    }
  }

  InputImage? _inputImageFromCameraImage(
    CameraImage image,
    InputImageRotation rotation,
  ) {
    final format = InputImageFormatValue.fromRawValue(image.format.raw);
    final expectedFormat = defaultTargetPlatform == TargetPlatform.android
        ? InputImageFormat.nv21
        : InputImageFormat.bgra8888;
    if (format != expectedFormat || image.planes.length != 1) return null;

    final plane = image.planes.first;
    return InputImage.fromBytes(
      bytes: plane.bytes,
      metadata: InputImageMetadata(
        size: Size(image.width.toDouble(), image.height.toDouble()),
        rotation: rotation,
        format: format!,
        bytesPerRow: plane.bytesPerRow,
      ),
    );
  }

  InputImageRotation? _rotationFor(CameraDescription description) {
    if (defaultTargetPlatform == TargetPlatform.iOS) {
      return InputImageRotationValue.fromRawValue(
        description.sensorOrientation,
      );
    }
    final orientations = <DeviceOrientation, int>{
      DeviceOrientation.portraitUp: 0,
      DeviceOrientation.landscapeLeft: 90,
      DeviceOrientation.portraitDown: 180,
      DeviceOrientation.landscapeRight: 270,
    };
    var compensation = orientations[_camera?.value.deviceOrientation];
    if (compensation == null) return null;
    if (description.lensDirection == CameraLensDirection.front) {
      compensation = (description.sensorOrientation + compensation) % 360;
    } else {
      compensation = (description.sensorOrientation - compensation + 360) % 360;
    }
    return InputImageRotationValue.fromRawValue(compensation);
  }

  static int _degrees(InputImageRotation rotation) => switch (rotation) {
    InputImageRotation.rotation0deg => 0,
    InputImageRotation.rotation90deg => 90,
    InputImageRotation.rotation180deg => 180,
    InputImageRotation.rotation270deg => 270,
  };

  String _cameraError(Object error) {
    if (error is TimeoutException) {
      return 'La cámara tardó demasiado en iniciar. Intenta de nuevo.';
    }
    if (error is CameraException) {
      return switch (error.code) {
        'CameraAccessDenied' => 'Permiso de cámara denegado.',
        'CameraAccessDeniedWithoutPrompt' =>
          'Activa el permiso de cámara desde Ajustes.',
        'CameraAccessRestricted' => 'El acceso a la cámara está restringido.',
        'cameraPermission' => 'No se pudo obtener el permiso de cámara.',
        _ => 'No se pudo iniciar la cámara. Intenta nuevamente.',
      };
    }
    return 'La cámara no está disponible en este dispositivo.';
  }

  // ----------------------------------------------------------------- UI

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.black,
    child: SafeArea(
      child: Column(
        children: [
          _buildHeader(),
          Expanded(child: _buildBody()),
        ],
      ),
    ),
  );

  Widget _buildHeader() => Padding(
    padding: const EdgeInsets.fromLTRB(16, 8, 4, 8),
    child: Row(
      children: [
        const Icon(Icons.checkroom_outlined, color: Colors.white),
        const SizedBox(width: 9),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'VESTIDOR VIRTUAL',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5,
                ),
              ),
              Text(
                '${widget.productName} · ${widget.variant.colorName} / ${widget.variant.sizeName}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        IconButton(
          tooltip: 'Ver puntos',
          isSelected: _showPoints,
          selectedIcon: const Icon(Icons.polyline, color: Color(0xFF00E5FF)),
          onPressed: () => setState(() => _showPoints = !_showPoints),
          icon: const Icon(Icons.polyline_outlined, color: Colors.white70),
        ),
        IconButton(
          tooltip: 'Espejo',
          isSelected: _mirror,
          selectedIcon: const Icon(Icons.flip, color: Colors.white),
          onPressed: () => setState(() => _mirror = !_mirror),
          icon: const Icon(Icons.flip, color: Colors.white38),
        ),
        IconButton(
          tooltip: 'Cerrar',
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.close, color: Colors.white),
        ),
      ],
    ),
  );

  Widget _buildBody() {
    if (_loading) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 14),
            Text('Iniciando cámara…', style: TextStyle(color: Colors.white)),
          ],
        ),
      );
    }
    final camera = _camera;
    if (_error != null || camera == null) {
      return _ErrorState(
        message: _error ?? 'La cámara no está disponible.',
        onRetry: _retry,
        onClose: () => Navigator.of(context).pop(),
      );
    }
    return _buildCameraStage(camera);
  }

  Size _portraitPreviewSize(CameraController camera) {
    final size = camera.value.previewSize ?? const Size(480, 640);
    return Size(
      math.min(size.width, size.height),
      math.max(size.width, size.height),
    );
  }

  Widget _buildCameraStage(CameraController camera) {
    final preview = _portraitPreviewSize(camera);
    final pose = _tracker.pose;
    final color = _colorFromHex(widget.variant.colorHex);
    return Stack(
      fit: StackFit.expand,
      children: [
        ClipRect(
          child: FittedBox(
            fit: BoxFit.cover,
            clipBehavior: Clip.hardEdge,
            child: SizedBox(
              width: preview.width,
              height: preview.height,
              child: CameraPreview(camera),
            ),
          ),
        ),
        Positioned.fill(
          child: IgnorePointer(
            child: CustomPaint(
              painter: GarmentPainter(
                pose: pose,
                previewSize: preview,
                garment: _garment,
                fallbackColor: color,
                sleeves: _sleeves,
                scale: _garmentIsOverlay ? widget.overlayScale : 1,
                showPoints: _showPoints,
              ),
            ),
          ),
        ),
        if (pose == null)
          const Positioned(top: 18, left: 18, right: 18, child: _PoseHint()),
        Positioned(left: 12, right: 12, bottom: 12, child: _buildNotice()),
      ],
    );
  }

  static Color _colorFromHex(String? hex) {
    final value = hex?.replaceAll('#', '').trim();
    if (value == null || value.length != 6) return const Color(0xFFD62828);
    final parsed = int.tryParse(value, radix: 16);
    return parsed == null ? const Color(0xFFD62828) : Color(0xFF000000 | parsed);
  }

  Widget _buildNotice() {
    final String mode;
    if (_garment == null) {
      mode = _garmentFailed
          ? 'Sin imagen: se dibuja la silueta del color elegido.'
          : 'Cargando la prenda…';
    } else if (_garmentIsOverlay) {
      mode = 'Prenda: PNG del probador (fondo transparente).';
    } else {
      mode = 'Prenda: foto del producto.';
    }
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 11, 14, 11),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: .78),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'Colocación automática',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 3),
          const Text(
            'La prenda sigue tus hombros y brazos. Mueve los brazos o inclínate '
            'para verla acompañarte; la cara se ignora por completo.',
            style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.3),
          ),
          const SizedBox(height: 5),
          Text(
            mode,
            style: const TextStyle(
              color: Colors.white54,
              fontSize: 11,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }
}

class _PoseHint extends StatelessWidget {
  const _PoseHint();

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: Colors.black.withValues(alpha: .65),
      borderRadius: BorderRadius.circular(12),
    ),
    child: const Padding(
      padding: EdgeInsets.all(12),
      child: Text(
        'Párate frente a la cámara, a 1–2 metros, para detectar tus hombros.',
        textAlign: TextAlign.center,
        style: TextStyle(color: Colors.white, height: 1.3),
      ),
    ),
  );
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({
    required this.message,
    required this.onRetry,
    required this.onClose,
  });

  final String message;
  final VoidCallback onRetry;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.camera_alt_outlined,
            color: Colors.white70,
            size: 48,
          ),
          const SizedBox(height: 14),
          Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Colors.white, height: 1.4),
          ),
          const SizedBox(height: 18),
          GcButton(label: 'Reintentar', onPressed: onRetry),
          const SizedBox(height: 10),
          GcButton(
            label: 'Cerrar',
            variant: GcButtonVariant.outlined,
            onPressed: onClose,
          ),
        ],
      ),
    ),
  );
}
