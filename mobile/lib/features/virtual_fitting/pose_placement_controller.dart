import 'dart:math' as math;

class PosePoint {
  const PosePoint(this.x, this.y, [this.z = 0]);

  final double x;
  final double y;

  /// Profundidad normalizada. En ML Kit, valores más negativos están
  /// normalmente más cerca de la cámara respecto al plano de la cadera.
  final double z;
}

class TorsoLandmarks {
  const TorsoLandmarks({
    required this.leftShoulder,
    required this.rightShoulder,
    required this.leftHip,
    required this.rightHip,
  });

  final PosePoint leftShoulder;
  final PosePoint rightShoulder;
  final PosePoint leftHip;
  final PosePoint rightHip;
}

class PosePlacement {
  const PosePlacement({
    required this.left,
    required this.top,
    required this.width,
    required this.height,
    required this.rotation,
    required this.pitch,
  });

  final double left;
  final double top;
  final double width;
  final double height;

  /// Inclinación lateral en radianes.
  final double rotation;

  /// Inclinación aproximada hacia delante/atrás en radianes.
  final double pitch;

  // Conserva tus ajustes actuales.
  static const double _topLift = 0.24;
  static const double _shoulderWidthScale = 2.0;
  static const double _heightScale = 1.58;

  // Sensibilidad de movimiento.
  static const double _sideLeanSensitivity = 1.0;
  static const double _depthSensitivity = 2.2;

  static PosePlacement? fromLandmarks(TorsoLandmarks landmarks) {
    final points = [
      landmarks.leftShoulder,
      landmarks.rightShoulder,
      landmarks.leftHip,
      landmarks.rightHip,
    ];
    if (points.any((point) => !_isNormalized(point))) return null;

    final shoulderCenter = _midpoint(
      landmarks.leftShoulder,
      landmarks.rightShoulder,
    );
    final hipCenter = _midpoint(landmarks.leftHip, landmarks.rightHip);

    // Usamos la distancia real entre centro de hombros y caderas.
    // Así la altura no se reduce artificialmente cuando te inclinas al lado.
    final torsoLength = _distance(shoulderCenter, hipCenter);
    final shoulderWidth = _distance(
      landmarks.leftShoulder,
      landmarks.rightShoulder,
    );

    if (torsoLength < .04 || shoulderWidth < .04) return null;

    final width = (shoulderWidth * _shoulderWidthScale)
        .clamp(.12, .95)
        .toDouble();

    final height = (torsoLength * _heightScale).clamp(.18, .98).toDouble();

    // --- INCLINACIÓN LATERAL ---
    // Vertical = 0 rad. Si caderas se desplazan a un lado respecto a hombros,
    // la prenda rota acompañando el eje del torso.
    final torsoDx = hipCenter.x - shoulderCenter.x;
    final torsoDy = hipCenter.y - shoulderCenter.y;
    final torsoAngle = math.atan2(torsoDx, torsoDy);

    // También usamos un poco la inclinación de los hombros para que responda
    // mejor cuando bajas un hombro.
    final shoulderTilt = math.atan2(
      landmarks.rightShoulder.y - landmarks.leftShoulder.y,
      (landmarks.rightShoulder.x - landmarks.leftShoulder.x).abs(),
    );

    var rotation =
        (torsoAngle * .75 + shoulderTilt * .25) * _sideLeanSensitivity;
    rotation = rotation.clamp(-0.65, 0.65).toDouble();

    // --- HACIA DELANTE / ATRÁS ---
    // ML Kit da Z relativo. Comparamos hombros vs caderas.
    final shoulderZ =
        (landmarks.leftShoulder.z + landmarks.rightShoulder.z) / 2;
    final hipZ = (landmarks.leftHip.z + landmarks.rightHip.z) / 2;
    final depthDelta = shoulderZ - hipZ;

    // Se limita para evitar saltos grandes cuando Z es ruidoso.
    final pitch = (depthDelta * _depthSensitivity)
        .clamp(-0.45, 0.45)
        .toDouble();

    final centerX = shoulderCenter.x;
    final anchoredTop = shoulderCenter.y - torsoLength * _topLift;

    return PosePlacement(
      left: _clamp(centerX - width / 2, 0, 1 - width),
      top: _clamp(anchoredTop, 0, 1),
      width: width,
      height: height,
      rotation: rotation,
      pitch: pitch,
    );
  }

  PosePlacement blend(PosePlacement next, double amount) => PosePlacement(
    left: _lerp(left, next.left, amount),
    top: _lerp(top, next.top, amount),
    width: _lerp(width, next.width, amount),
    height: _lerp(height, next.height, amount),
    rotation: _lerp(rotation, next.rotation, amount),
    pitch: _lerp(pitch, next.pitch, amount),
  );

  static bool _isNormalized(PosePoint point) =>
      point.x.isFinite &&
      point.y.isFinite &&
      point.z.isFinite &&
      point.x >= 0 &&
      point.x <= 1 &&
      point.y >= 0 &&
      point.y <= 1;

  static PosePoint _midpoint(PosePoint first, PosePoint second) => PosePoint(
    (first.x + second.x) / 2,
    (first.y + second.y) / 2,
    (first.z + second.z) / 2,
  );

  static double _distance(PosePoint first, PosePoint second) => math.sqrt(
    math.pow(first.x - second.x, 2) + math.pow(first.y - second.y, 2),
  );

  static double _clamp(double value, double min, double max) =>
      value.clamp(min, max).toDouble();

  static double _lerp(double first, double second, double amount) =>
      first + (second - first) * amount;
}

/// Keeps the last valid placement when a camera frame is incomplete.
class PosePlacementController {
  PosePlacement? _placement;

  PosePlacement? get placement => _placement;

  bool update(TorsoLandmarks landmarks) {
    final next = PosePlacement.fromLandmarks(landmarks);
    if (next == null) return false;

    // Un poco más suave que antes porque ahora también rotamos en 2 ejes.
    _placement = _placement?.blend(next, .28) ?? next;
    return true;
  }
}
