import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';

import '../../shared/widgets/gc_button.dart';
import '../catalog/catalog_models.dart';
import 'pose_placement_controller.dart';

typedef CameraEnumerator = Future<List<CameraDescription>> Function();

class VirtualFittingSheet extends StatefulWidget {
  const VirtualFittingSheet({
    required this.productName,
    required this.variant,
    required this.imageUrl,
    this.cameraEnumerator,
    super.key,
  });

  final String productName;
  final Variant variant;
  final String imageUrl;
  final CameraEnumerator? cameraEnumerator;

  @override
  State<VirtualFittingSheet> createState() => _VirtualFittingSheetState();
}

class _VirtualFittingSheetState extends State<VirtualFittingSheet>
    with WidgetsBindingObserver {
  CameraController? _camera;
  PoseDetector? _poseDetector;
  final _placement = PosePlacementController();
  Map<PoseLandmarkType, PosePoint> _visibleLandmarks = const {};
  String? _error;
  bool _loading = true;
  bool _initializing = false;
  bool _processingFrame = false;
  DateTime? _lastProcessedAt;
  int _cameraGeneration = 0;

  bool get _mobilePlatform =>
      defaultTargetPlatform == TargetPlatform.android ||
      defaultTargetPlatform == TargetPlatform.iOS;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    if (widget.imageUrl.trim().isEmpty) {
      _loading = false;
      _error = 'No hay una imagen disponible para esta prenda.';
    } else if (!_mobilePlatform && widget.cameraEnumerator == null) {
      _loading = false;
      _error = 'El vestidor virtual solo está disponible en Android y iOS.';
    } else {
      unawaited(_initializeCamera());
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    unawaited(_disposeCamera());
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      if (_camera == null && !_initializing && _error == null) {
        unawaited(_initializeCamera());
      }
    } else if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.paused ||
        state == AppLifecycleState.detached) {
      unawaited(_disposeCamera());
    }
  }

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
      camera = CameraController(
        description,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: defaultTargetPlatform == TargetPlatform.android
            ? ImageFormatGroup.nv21
            : ImageFormatGroup.bgra8888,
      );
      await camera.initialize();
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
      if (!mounted || generation != _cameraGeneration) {
        await detector.close();
        await camera.dispose();
        return;
      }
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
    }
  }

  Future<void> _disposeCamera() async {
    _cameraGeneration++;
    final camera = _camera;
    final detector = _poseDetector;
    _camera = null;
    _poseDetector = null;
    _visibleLandmarks = const {};
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
    if (mounted && _error == null && !_initializing) {
      setState(() => _loading = false);
    }
  }

  Future<void> _processCameraImage(CameraImage image) async {
    if (_processingFrame || _poseDetector == null || _camera == null) return;
    final now = DateTime.now();
    if (_lastProcessedAt != null &&
        now.difference(_lastProcessedAt!) < const Duration(milliseconds: 180)) {
      return;
    }
    final inputImage = _inputImageFromCameraImage(image);
    if (inputImage == null) {
      debugPrint(
        '[POSE] Frame descartado: no se pudo crear InputImage. '
        'format=${InputImageFormatValue.fromRawValue(image.format.raw)} '
        'planes=${image.planes.length} size=${image.width}x${image.height}',
      );
      return;
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
      debugPrint('[POSE] ML Kit devolvió ${poses.length} pose(s)');
      final pose = poses.firstOrNull;
      if (pose == null) {
        if (_visibleLandmarks.isNotEmpty || _placement.placement == null) {
          setState(() => _visibleLandmarks = const {});
        }
        return;
      }

      final camera = _camera;
      if (camera == null) return;
      final rotation = _rotationFor(camera.description);
      if (rotation == null) {
        debugPrint('[POSE] No se pudo calcular la rotación del frame');
        return;
      }

      final visibleLandmarks = _normalizedPoseLandmarks(
        pose,
        image.width,
        image.height,
        rotation,
      );
      final landmarks = _torsoLandmarksFromMap(visibleLandmarks);

      if (landmarks == null) {
        debugPrint('[POSE] Pose encontrada, pero faltan landmarks del torso');
        setState(() => _visibleLandmarks = visibleLandmarks);
        return;
      }

      final updated = _placement.update(landmarks);
      if (updated) {
        debugPrint(
          '[POSE] Placement actualizado: '
          'L=${_placement.placement?.left.toStringAsFixed(3)} '
          'T=${_placement.placement?.top.toStringAsFixed(3)} '
          'W=${_placement.placement?.width.toStringAsFixed(3)} '
          'H=${_placement.placement?.height.toStringAsFixed(3)}',
        );
      } else {
        debugPrint(
          '[POSE] Landmarks recibidos, pero PosePlacement los rechazó',
        );
      }

      setState(() => _visibleLandmarks = visibleLandmarks);
    } catch (error, stackTrace) {
      debugPrint('[POSE] Error procesando frame: $error');
      debugPrintStack(stackTrace: stackTrace);
    } finally {
      _processingFrame = false;
    }
  }

  InputImage? _inputImageFromCameraImage(CameraImage image) {
    final camera = _camera;
    if (camera == null) return null;

    final rotation = _rotationFor(camera.description);
    if (rotation == null) {
      debugPrint('[POSE] Rotación inválida');
      return null;
    }

    final format = InputImageFormatValue.fromRawValue(image.format.raw);
    final expectedFormat = defaultTargetPlatform == TargetPlatform.android
        ? InputImageFormat.nv21
        : InputImageFormat.bgra8888;

    if (format != expectedFormat) {
      debugPrint(
        '[POSE] Formato no soportado. recibido=$format esperado=$expectedFormat',
      );
      return null;
    }

    if (image.planes.length != 1) {
      debugPrint(
        '[POSE] Número de planos no soportado: ${image.planes.length}. '
        'NV21/BGRA8888 debe llegar como un solo plano.',
      );
      return null;
    }

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

  Map<PoseLandmarkType, PosePoint> _normalizedPoseLandmarks(
    Pose pose,
    int width,
    int height,
    InputImageRotation rotation,
  ) {
    final camera = _camera;
    if (camera == null || width <= 0 || height <= 0) return const {};

    final result = <PoseLandmarkType, PosePoint>{};

    // Para el vestidor ignoramos por completo los landmarks de la cara.
    // ML Kit puede detectarlos internamente, pero no se dibujan ni se usan
    // para calcular la colocación de la prenda.
    const ignoredFaceLandmarks = <PoseLandmarkType>{
      PoseLandmarkType.nose,
      PoseLandmarkType.leftEyeInner,
      PoseLandmarkType.leftEye,
      PoseLandmarkType.leftEyeOuter,
      PoseLandmarkType.rightEyeInner,
      PoseLandmarkType.rightEye,
      PoseLandmarkType.rightEyeOuter,
      PoseLandmarkType.leftEar,
      PoseLandmarkType.rightEar,
      PoseLandmarkType.leftMouth,
      PoseLandmarkType.rightMouth,
    };

    for (final entry in pose.landmarks.entries) {
      if (ignoredFaceLandmarks.contains(entry.key)) continue;

      final landmark = entry.value;
      double x;
      double y;

      // Conservamos exactamente la misma conversión que utiliza la prenda.
      switch (rotation) {
        case InputImageRotation.rotation90deg:
          x =
              landmark.x /
              (defaultTargetPlatform == TargetPlatform.iOS ? width : height);
          y =
              landmark.y /
              (defaultTargetPlatform == TargetPlatform.iOS ? height : width);
          break;
        case InputImageRotation.rotation270deg:
          x =
              1 -
              landmark.x /
                  (defaultTargetPlatform == TargetPlatform.iOS
                      ? width
                      : height);
          y =
              landmark.y /
              (defaultTargetPlatform == TargetPlatform.iOS ? height : width);
          break;
        case InputImageRotation.rotation0deg:
        case InputImageRotation.rotation180deg:
          x = landmark.x / width;
          y = landmark.y / height;
          if (camera.description.lensDirection == CameraLensDirection.front) {
            x = 1 - x;
          }
          break;
      }

      if (!x.isFinite || !y.isFinite) continue;

      // Dibujamos únicamente puntos visibles dentro del preview.
      if (x < 0 || x > 1 || y < 0 || y > 1) continue;

      result[entry.key] = PosePoint(x, y);
    }

    for (final type in const [
      PoseLandmarkType.leftShoulder,
      PoseLandmarkType.rightShoulder,
      PoseLandmarkType.leftHip,
      PoseLandmarkType.rightHip,
    ]) {
      final point = result[type];
      final raw = pose.landmarks[type];
      if (point != null && raw != null) {
        debugPrint(
          '[POSE] $type raw=(${raw.x.toStringAsFixed(1)}, '
          '${raw.y.toStringAsFixed(1)}) normalized='
          '(${point.x.toStringAsFixed(3)}, ${point.y.toStringAsFixed(3)}) '
          'rotation=$rotation',
        );
      }
    }

    return result;
  }

  TorsoLandmarks? _torsoLandmarksFromMap(
    Map<PoseLandmarkType, PosePoint> points,
  ) {
    final leftShoulder = points[PoseLandmarkType.leftShoulder];
    final rightShoulder = points[PoseLandmarkType.rightShoulder];
    final leftHip = points[PoseLandmarkType.leftHip];
    final rightHip = points[PoseLandmarkType.rightHip];

    if (leftShoulder == null ||
        rightShoulder == null ||
        leftHip == null ||
        rightHip == null) {
      return null;
    }

    return TorsoLandmarks(
      leftShoulder: leftShoulder,
      rightShoulder: rightShoulder,
      leftHip: leftHip,
      rightHip: rightHip,
    );
  }

  String _cameraError(Object error) {
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
    padding: const EdgeInsets.fromLTRB(16, 8, 8, 8),
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
    if (_error != null || _camera == null) {
      return _ErrorState(
        message: _error ?? 'La cámara no está disponible.',
        onClose: () => Navigator.of(context).pop(),
      );
    }
    return _buildCameraStage(_camera!);
  }

  Widget _buildCameraStage(CameraController camera) => LayoutBuilder(
    builder: (context, constraints) {
      final placement = _placement.placement;
      return Stack(
        fit: StackFit.expand,
        children: [
          CameraPreview(camera),
          if (placement != null)
            Positioned(
              left: placement.left * constraints.maxWidth,
              top: placement.top * constraints.maxHeight,
              width: placement.width * constraints.maxWidth,
              height: placement.height * constraints.maxHeight,
              child: IgnorePointer(
                child: Opacity(
                  opacity: .72,
                  child: Image.network(
                    widget.imageUrl,
                    fit: BoxFit.contain,
                    alignment: Alignment.topCenter,
                    errorBuilder: (_, _, _) => const Center(
                      child: Icon(
                        Icons.broken_image_outlined,
                        color: Colors.white,
                        size: 40,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          if (_visibleLandmarks.isNotEmpty)
            Positioned.fill(
              child: IgnorePointer(
                child: CustomPaint(
                  painter: _PoseLandmarksPainter(_visibleLandmarks),
                ),
              ),
            ),
          if (placement == null)
            const Positioned(top: 18, left: 18, right: 18, child: _PoseHint()),
          Positioned(left: 12, right: 12, bottom: 12, child: _buildNotice()),
        ],
      );
    },
  );

  Widget _buildNotice() => Container(
    padding: const EdgeInsets.fromLTRB(14, 11, 14, 11),
    decoration: BoxDecoration(
      color: Colors.black.withValues(alpha: .78),
      borderRadius: BorderRadius.circular(16),
    ),
    child: const Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Colocación automática',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800),
        ),
        SizedBox(height: 3),
        Text(
          'Usamos solo el cuerpo desde los hombros hacia abajo. La cara se ignora por completo.',
          style: TextStyle(color: Colors.white70, fontSize: 12, height: 1.3),
        ),
        SizedBox(height: 5),
        Text(
          'La imagen puede incluir fondo y se muestra tal como está.',
          style: TextStyle(color: Colors.white54, fontSize: 11, height: 1.3),
        ),
      ],
    ),
  );
}

class _PoseLandmarksPainter extends CustomPainter {
  const _PoseLandmarksPainter(this.landmarks);

  final Map<PoseLandmarkType, PosePoint> landmarks;

  static const _torsoTypes = <PoseLandmarkType>{
    PoseLandmarkType.leftShoulder,
    PoseLandmarkType.rightShoulder,
    PoseLandmarkType.leftHip,
    PoseLandmarkType.rightHip,
  };

  static const _connections = <(PoseLandmarkType, PoseLandmarkType)>[
    (PoseLandmarkType.leftShoulder, PoseLandmarkType.rightShoulder),
    (PoseLandmarkType.leftShoulder, PoseLandmarkType.leftHip),
    (PoseLandmarkType.rightShoulder, PoseLandmarkType.rightHip),
    (PoseLandmarkType.leftHip, PoseLandmarkType.rightHip),
    (PoseLandmarkType.leftShoulder, PoseLandmarkType.leftElbow),
    (PoseLandmarkType.leftElbow, PoseLandmarkType.leftWrist),
    (PoseLandmarkType.rightShoulder, PoseLandmarkType.rightElbow),
    (PoseLandmarkType.rightElbow, PoseLandmarkType.rightWrist),
    (PoseLandmarkType.leftHip, PoseLandmarkType.leftKnee),
    (PoseLandmarkType.leftKnee, PoseLandmarkType.leftAnkle),
    (PoseLandmarkType.rightHip, PoseLandmarkType.rightKnee),
    (PoseLandmarkType.rightKnee, PoseLandmarkType.rightAnkle),
  ];

  Offset _offset(PosePoint point, Size size) =>
      Offset(point.x * size.width, point.y * size.height);

  @override
  void paint(Canvas canvas, Size size) {
    final skeletonPaint = Paint()
      ..color = Colors.cyanAccent.withValues(alpha: .9)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    for (final connection in _connections) {
      final first = landmarks[connection.$1];
      final second = landmarks[connection.$2];
      if (first == null || second == null) continue;
      canvas.drawLine(
        _offset(first, size),
        _offset(second, size),
        skeletonPaint,
      );
    }

    final normalPointPaint = Paint()
      ..color = Colors.yellowAccent
      ..style = PaintingStyle.fill;
    final torsoPointPaint = Paint()
      ..color = Colors.redAccent
      ..style = PaintingStyle.fill;
    final outlinePaint = Paint()
      ..color = Colors.black
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    for (final entry in landmarks.entries) {
      final position = _offset(entry.value, size);
      final isTorso = _torsoTypes.contains(entry.key);
      final radius = isTorso ? 7.0 : 4.0;
      canvas.drawCircle(
        position,
        radius,
        isTorso ? torsoPointPaint : normalPointPaint,
      );
      canvas.drawCircle(position, radius, outlinePaint);
    }

    _drawLabel(canvas, size, PoseLandmarkType.leftShoulder, 'Hombro I');
    _drawLabel(canvas, size, PoseLandmarkType.rightShoulder, 'Hombro D');
    _drawLabel(canvas, size, PoseLandmarkType.leftHip, 'Cadera I');
    _drawLabel(canvas, size, PoseLandmarkType.rightHip, 'Cadera D');
  }

  void _drawLabel(
    Canvas canvas,
    Size size,
    PoseLandmarkType type,
    String label,
  ) {
    final point = landmarks[type];
    if (point == null) return;

    final position = _offset(point, size);
    final textPainter = TextPainter(
      text: TextSpan(
        text: label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 10,
          fontWeight: FontWeight.w700,
          shadows: [Shadow(color: Colors.black, blurRadius: 3)],
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();

    textPainter.paint(canvas, position + const Offset(9, -13));
  }

  @override
  bool shouldRepaint(covariant _PoseLandmarksPainter oldDelegate) =>
      oldDelegate.landmarks != landmarks;
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
        'Párate frente a la cámara para detectar hombros y cadera.',
        textAlign: TextAlign.center,
        style: TextStyle(color: Colors.white, height: 1.3),
      ),
    ),
  );
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onClose});

  final String message;
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
