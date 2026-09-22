import 'dart:math' as math;

/// Articulaciones en el mismo orden y nombre que `PoseLandmarkType` de ML Kit,
/// para poder convertir por nombre sin depender del paquete en este archivo.
enum BodyJoint {
  nose,
  leftEyeInner,
  leftEye,
  leftEyeOuter,
  rightEyeInner,
  rightEye,
  rightEyeOuter,
  leftEar,
  rightEar,
  leftMouth,
  rightMouth,
  leftShoulder,
  rightShoulder,
  leftElbow,
  rightElbow,
  leftWrist,
  rightWrist,
  leftPinky,
  rightPinky,
  leftIndex,
  rightIndex,
  leftThumb,
  rightThumb,
  leftHip,
  rightHip,
  leftKnee,
  rightKnee,
  leftAnkle,
  rightAnkle,
  leftHeel,
  rightHeel,
  leftFootIndex,
  rightFootIndex,
}

/// Conexiones del esqueleto que se dibujan con "Ver puntos".
const List<(BodyJoint, BodyJoint)> skeletonBones = [
  (BodyJoint.leftShoulder, BodyJoint.rightShoulder),
  (BodyJoint.leftShoulder, BodyJoint.leftElbow),
  (BodyJoint.leftElbow, BodyJoint.leftWrist),
  (BodyJoint.rightShoulder, BodyJoint.rightElbow),
  (BodyJoint.rightElbow, BodyJoint.rightWrist),
  (BodyJoint.leftShoulder, BodyJoint.leftHip),
  (BodyJoint.rightShoulder, BodyJoint.rightHip),
  (BodyJoint.leftHip, BodyJoint.rightHip),
  (BodyJoint.leftHip, BodyJoint.leftKnee),
  (BodyJoint.leftKnee, BodyJoint.leftAnkle),
  (BodyJoint.rightHip, BodyJoint.rightKnee),
  (BodyJoint.rightKnee, BodyJoint.rightAnkle),
];

class BodyPoint {
  const BodyPoint(this.x, this.y, [this.likelihood = 1]);

  final double x;
  final double y;
  final double likelihood;

  BodyPoint lerp(BodyPoint other, double amount) => BodyPoint(
    x + (other.x - x) * amount,
    y + (other.y - y) * amount,
    other.likelihood,
  );
}

/// Pose normalizada (0..1 sobre el frame ya rotado y, si corresponde,
/// espejado). Hombros siempre presentes; caderas, codos y muñecas pueden
/// venir estimados cuando ML Kit no los ve.
class BodyPose {
  const BodyPose(this.points, {this.estimated = const {}});

  final Map<BodyJoint, BodyPoint> points;
  final Set<BodyJoint> estimated;

  BodyPoint operator [](BodyJoint joint) => points[joint]!;

  static const double _minLikelihood = .5;

  /// [raw] viene en píxeles del buffer original (`imageWidth` x `imageHeight`)
  /// y ML Kit ya lo devuelve en el marco rotado. Con rotación 90/270 el ancho y
  /// alto quedan intercambiados. [mirror] refleja horizontalmente (cámara
  /// frontal, cuyo preview se ve en espejo).
  static BodyPose? fromLandmarks({
    required Map<BodyJoint, BodyPoint> raw,
    required int imageWidth,
    required int imageHeight,
    required int rotationDegrees,
    required bool mirror,
  }) {
    if (imageWidth <= 0 || imageHeight <= 0) return null;
    final rotated = rotationDegrees == 90 || rotationDegrees == 270;
    final frameWidth = (rotated ? imageHeight : imageWidth).toDouble();
    final frameHeight = (rotated ? imageWidth : imageHeight).toDouble();

    final points = <BodyJoint, BodyPoint>{};
    raw.forEach((joint, point) {
      if (!point.x.isFinite || !point.y.isFinite) return;
      var x = point.x / frameWidth;
      final y = point.y / frameHeight;
      if (mirror) x = 1 - x;
      points[joint] = BodyPoint(x, y, point.likelihood);
    });

    final leftShoulder = points[BodyJoint.leftShoulder];
    final rightShoulder = points[BodyJoint.rightShoulder];
    if (!_visible(leftShoulder) || !_visible(rightShoulder)) return null;
    if (!_inFrame(leftShoulder!) || !_inFrame(rightShoulder!)) return null;

    final sw = _distance(leftShoulder, rightShoulder);
    if (sw < .04) return null;

    final estimated = <BodyJoint>{};
    final across = _unit(
      leftShoulder.x - rightShoulder.x,
      leftShoulder.y - rightShoulder.y,
    );
    // Perpendicular a la línea de hombros, siempre hacia abajo en pantalla.
    var down = (-across.$2, across.$1);
    if (down.$2 < 0) down = (-down.$1, -down.$2);
    final outLeft = _unit(
      leftShoulder.x - rightShoulder.x,
      leftShoulder.y - rightShoulder.y,
    );
    final outRight = (-outLeft.$1, -outLeft.$2);

    void estimateSide(
      BodyPoint shoulder,
      (double, double) outward,
      BodyJoint hip,
      BodyJoint elbow,
      BodyJoint wrist,
    ) {
      if (!_visible(points[hip])) {
        points[hip] = BodyPoint(
          shoulder.x + down.$1 * sw * 1.3 - outward.$1 * sw * .12,
          shoulder.y + down.$2 * sw * 1.3 - outward.$2 * sw * .12,
          0,
        );
        estimated.add(hip);
      }
      if (!_visible(points[elbow])) {
        points[elbow] = BodyPoint(
          shoulder.x + down.$1 * sw * .7 + outward.$1 * sw * .15,
          shoulder.y + down.$2 * sw * .7 + outward.$2 * sw * .15,
          0,
        );
        estimated.add(elbow);
      }
      if (!_visible(points[wrist])) {
        final e = points[elbow]!;
        points[wrist] = BodyPoint(
          e.x + down.$1 * sw * .7,
          e.y + down.$2 * sw * .7,
          0,
        );
        estimated.add(wrist);
      }
    }

    estimateSide(
      leftShoulder,
      outLeft,
      BodyJoint.leftHip,
      BodyJoint.leftElbow,
      BodyJoint.leftWrist,
    );
    estimateSide(
      rightShoulder,
      outRight,
      BodyJoint.rightHip,
      BodyJoint.rightElbow,
      BodyJoint.rightWrist,
    );
    return BodyPose(points, estimated: estimated);
  }

  static bool _visible(BodyPoint? point) =>
      point != null && point.likelihood >= _minLikelihood;

  static bool _inFrame(BodyPoint point) =>
      point.x >= -.1 && point.x <= 1.1 && point.y >= -.1 && point.y <= 1.1;

  static double _distance(BodyPoint a, BodyPoint b) =>
      math.sqrt(math.pow(a.x - b.x, 2) + math.pow(a.y - b.y, 2));

  static (double, double) _unit(double dx, double dy) {
    final length = math.sqrt(dx * dx + dy * dy);
    if (length == 0) return (1, 0);
    return (dx / length, dy / length);
  }
}

/// Suaviza las poses frame a frame y olvida el cuerpo si deja de verse.
class BodyTracker {
  BodyTracker({
    DateTime Function()? now,
    this.smoothing = .5,
    this.lostAfter = const Duration(milliseconds: 1200),
  }) : _now = now ?? DateTime.now;

  final DateTime Function() _now;
  final double smoothing;
  final Duration lostAfter;

  BodyPose? _pose;
  DateTime? _lastSeen;

  BodyPose? get pose => _pose;

  /// Devuelve `true` si la pose visible cambió (nueva pose o cuerpo perdido).
  bool update(BodyPose? next) {
    final now = _now();
    if (next == null) {
      final seen = _lastSeen;
      if (_pose != null && seen != null && now.difference(seen) > lostAfter) {
        clear();
        return true;
      }
      return false;
    }
    _lastSeen = now;
    final previous = _pose;
    if (previous == null) {
      _pose = next;
      return true;
    }
    final blended = <BodyJoint, BodyPoint>{};
    next.points.forEach((joint, point) {
      final before = previous.points[joint];
      blended[joint] = before == null ? point : before.lerp(point, smoothing);
    });
    _pose = BodyPose(blended, estimated: next.estimated);
    return true;
  }

  void clear() {
    _pose = null;
    _lastSeen = null;
  }
}

enum SleeveMode { none, short, long }

/// Dónde se cuelga la prenda: en los hombros (partes de arriba, vestidos) o
/// en la cadera (pantalones, faldas).
enum GarmentAnchor { shoulders, hips }

GarmentAnchor anchorFor(String productName) {
  final name = productName.toLowerCase();
  const hips = ['jean', 'pantal', 'jogger', 'falda', 'short', 'bermuda'];
  return hips.any(name.contains) ? GarmentAnchor.hips : GarmentAnchor.shoulders;
}

/// Deduce el largo de manga por el nombre del producto (el catálogo no manda
/// el nombre de la categoría).
SleeveMode sleeveModeFor(String productName) {
  final name = productName.toLowerCase();
  const long = ['camisa', 'chamarra', 'parka', 'abrigo', 'chaqueta', 'buzo'];
  const none = ['vestido', 'falda', 'jean', 'pantal', 'jogger', 'short'];
  if (long.any(name.contains)) return SleeveMode.long;
  if (none.any(name.contains)) return SleeveMode.none;
  return SleeveMode.short;
}

class ArmSegment {
  const ArmSegment({
    required this.start,
    required this.end,
    required this.angle,
    required this.estimated,
  });

  final math.Point<double> start;
  final math.Point<double> end;

  /// Ángulo en radianes medido desde +x (hacia la derecha) en pantalla.
  final double angle;
  final bool estimated;

  double get length => start.distanceTo(end);
}

class ArmGeometry {
  const ArmGeometry({required this.upper, required this.lower});

  /// Hombro → codo.
  final ArmSegment upper;

  /// Codo → muñeca.
  final ArmSegment lower;
}

/// Medidas de la prenda en píxeles de pantalla, calculadas a partir de la pose
/// ya proyectada con [map] (las coordenadas normalizadas no son isotrópicas,
/// por eso los ángulos se calculan después de proyectar).
class GarmentGeometry {
  const GarmentGeometry({
    required this.shoulderMid,
    required this.hipMid,
    required this.shoulderWidth,
    required this.torsoLength,
    required this.angle,
    required this.leftShoulder,
    required this.rightShoulder,
    required this.leftHip,
    required this.rightHip,
    required this.leftArm,
    required this.rightArm,
  });

  final math.Point<double> shoulderMid;
  final math.Point<double> hipMid;
  final math.Point<double> leftShoulder;
  final math.Point<double> rightShoulder;
  final math.Point<double> leftHip;
  final math.Point<double> rightHip;

  double get hipWidth => leftHip.distanceTo(rightHip);

  /// Inclinación de la línea de cadera, en (-π/2, π/2).
  double get hipAngle {
    var dx = leftHip.x - rightHip.x;
    var dy = leftHip.y - rightHip.y;
    if (dx < 0) {
      dx = -dx;
      dy = -dy;
    }
    return math.atan2(dy, dx);
  }

  /// Distancia entre hombros en píxeles: la única escala de la prenda.
  final double shoulderWidth;
  final double torsoLength;

  /// Inclinación de la línea de hombros en radianes (0 = horizontal), siempre
  /// en (-π/2, π/2) para que la prenda nunca se dibuje al revés.
  final double angle;
  final ArmGeometry leftArm;
  final ArmGeometry rightArm;

  /// Hombro que queda a la izquierda en pantalla (con espejo, el izquierdo de
  /// la persona).
  math.Point<double> get screenLeftShoulder =>
      leftShoulder.x <= rightShoulder.x ? leftShoulder : rightShoulder;

  math.Point<double> get screenRightShoulder =>
      leftShoulder.x <= rightShoulder.x ? rightShoulder : leftShoulder;

  ArmGeometry get screenLeftArm =>
      leftShoulder.x <= rightShoulder.x ? leftArm : rightArm;

  ArmGeometry get screenRightArm =>
      leftShoulder.x <= rightShoulder.x ? rightArm : leftArm;

  static GarmentGeometry compute(
    BodyPose pose,
    math.Point<double> Function(BodyPoint point) map,
  ) {
    final ls = map(pose[BodyJoint.leftShoulder]);
    final rs = map(pose[BodyJoint.rightShoulder]);
    final lh = map(pose[BodyJoint.leftHip]);
    final rh = map(pose[BodyJoint.rightHip]);
    final shoulderMid = _mid(ls, rs);
    final hipMid = _mid(lh, rh);

    var dx = ls.x - rs.x;
    var dy = ls.y - rs.y;
    if (dx < 0) {
      dx = -dx;
      dy = -dy;
    }
    return GarmentGeometry(
      shoulderMid: shoulderMid,
      hipMid: hipMid,
      shoulderWidth: ls.distanceTo(rs),
      torsoLength: shoulderMid.distanceTo(hipMid),
      angle: math.atan2(dy, dx),
      leftShoulder: ls,
      rightShoulder: rs,
      leftHip: lh,
      rightHip: rh,
      leftArm: _arm(
        pose,
        map,
        BodyJoint.leftShoulder,
        BodyJoint.leftElbow,
        BodyJoint.leftWrist,
      ),
      rightArm: _arm(
        pose,
        map,
        BodyJoint.rightShoulder,
        BodyJoint.rightElbow,
        BodyJoint.rightWrist,
      ),
    );
  }

  static ArmGeometry _arm(
    BodyPose pose,
    math.Point<double> Function(BodyPoint point) map,
    BodyJoint shoulder,
    BodyJoint elbow,
    BodyJoint wrist,
  ) {
    final s = map(pose[shoulder]);
    final e = map(pose[elbow]);
    final w = map(pose[wrist]);
    return ArmGeometry(
      upper: ArmSegment(
        start: s,
        end: e,
        angle: math.atan2(e.y - s.y, e.x - s.x),
        estimated: pose.estimated.contains(elbow),
      ),
      lower: ArmSegment(
        start: e,
        end: w,
        angle: math.atan2(w.y - e.y, w.x - e.x),
        estimated: pose.estimated.contains(wrist),
      ),
    );
  }

  static math.Point<double> _mid(math.Point<double> a, math.Point<double> b) =>
      math.Point((a.x + b.x) / 2, (a.y + b.y) / 2);
}
