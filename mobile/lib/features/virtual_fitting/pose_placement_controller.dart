import 'dart:math' as math;

class PosePoint {
  const PosePoint(this.x, this.y);

  final double x;
  final double y;
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
  });

  final double left;
  final double top;
  final double width;
  final double height;

  // Ajustes finos del vestidor.
  // Si quieres subir más la prenda, aumenta _topLift.
  // Si quieres hacerla más ancha, aumenta _shoulderWidthScale.
  static const double _topLift = 0.24;
  static const double _shoulderWidthScale = 2.0;
  static const double _heightScale = 1.58;

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

    final torsoHeight = hipCenter.y - shoulderCenter.y;
    final shoulderWidth = _distance(
      landmarks.leftShoulder,
      landmarks.rightShoulder,
    );

    if (torsoHeight < .04 || shoulderWidth < .04) {
      return null;
    }

    // El ancho se calcula principalmente con los hombros.
    final width = (shoulderWidth * _shoulderWidthScale)
        .clamp(.12, .95)
        .toDouble();

    // La altura sigue el torso.
    final height = (torsoHeight * _heightScale).clamp(.18, .98).toDouble();

    final centerX = shoulderCenter.x;

    // Subimos la prenda respecto a la línea de hombros.
    final anchoredTop = shoulderCenter.y - torsoHeight * _topLift;

    return PosePlacement(
      left: _clamp(centerX - width / 2, 0, 1 - width),
      top: _clamp(anchoredTop, 0, 1),
      width: width,
      height: height,
    );
  }

  PosePlacement blend(PosePlacement next, double amount) => PosePlacement(
    left: _lerp(left, next.left, amount),
    top: _lerp(top, next.top, amount),
    width: _lerp(width, next.width, amount),
    height: _lerp(height, next.height, amount),
  );

  static bool _isNormalized(PosePoint point) =>
      point.x.isFinite &&
      point.y.isFinite &&
      point.x >= 0 &&
      point.x <= 1 &&
      point.y >= 0 &&
      point.y <= 1;

  static PosePoint _midpoint(PosePoint first, PosePoint second) =>
      PosePoint((first.x + second.x) / 2, (first.y + second.y) / 2);

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
    _placement = _placement?.blend(next, .35) ?? next;
    return true;
  }
}
