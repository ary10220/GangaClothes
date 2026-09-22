import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import 'body_model.dart';

/// Proyecta coordenadas normalizadas del frame al stage usando la misma
/// transformación `cover` con la que se muestra el preview de la cámara.
class PreviewMapper {
  PreviewMapper({required this.stage, required this.preview})
    : scale = math.max(stage.width / preview.width, stage.height / preview.height) {
    dx = (stage.width - preview.width * scale) / 2;
    dy = (stage.height - preview.height * scale) / 2;
  }

  final Size stage;

  /// Tamaño del preview ya en orientación vertical (ancho < alto).
  final Size preview;
  final double scale;
  late final double dx;
  late final double dy;

  Offset map(double x, double y) =>
      Offset(dx + x * preview.width * scale, dy + y * preview.height * scale);

  math.Point<double> point(BodyPoint p) {
    final o = map(p.x, p.y);
    return math.Point(o.dx, o.dy);
  }
}

/// Dibuja la prenda (PNG recortado o forma vectorial) siguiendo hombros y
/// brazos, y opcionalmente los puntos del cuerpo.
class GarmentPainter extends CustomPainter {
  const GarmentPainter({
    required this.pose,
    required this.previewSize,
    required this.garment,
    required this.fallbackColor,
    required this.sleeves,
    required this.scale,
    required this.showPoints,
    this.showGarment = true,
  });

  final BodyPose? pose;
  final Size previewSize;
  final ui.Image? garment;
  final Color fallbackColor;
  final SleeveMode sleeves;

  /// `escala` del recurso AR: multiplica el ancho de la prenda.
  final double scale;
  final bool showPoints;
  final bool showGarment;

  // Proporciones del PNG (ya recortado a la silueta): los hombros caen en
  // x = 25 % / 75 % del ancho y en y = 8 % del alto; las mangas viven en las
  // franjas laterales.
  static const double _shoulderX = .25;
  static const double _shoulderY = .08;
  static const double _shortSleeveBottom = .45;
  static const double _elbowY = .45;
  static const double _longSleeveBottom = .82;

  /// Ángulo (respecto de la vertical) con el que cuelgan las mangas en la foto.
  static const double _restSpread = .30;

  @override
  void paint(Canvas canvas, Size size) {
    final pose = this.pose;
    if (pose == null || size.isEmpty) return;
    final mapper = PreviewMapper(stage: size, preview: previewSize);
    final geometry = GarmentGeometry.compute(pose, mapper.point);
    if (geometry.shoulderWidth < 8) return;

    if (showGarment) {
      final image = garment;
      if (image != null) {
        _paintImage(canvas, geometry, image);
      } else {
        _paintVector(canvas, geometry);
      }
    }
    if (showPoints) _paintPoints(canvas, pose, mapper);
  }

  // --------------------------------------------------------------- PNG

  void _paintImage(Canvas canvas, GarmentGeometry g, ui.Image image) {
    final w = image.width.toDouble();
    final h = image.height.toDouble();
    // La distancia entre hombros ocupa la mitad del ancho de la foto.
    final s = g.shoulderWidth * scale / (w * (1 - 2 * _shoulderX));
    final paint = Paint()..filterQuality = FilterQuality.medium;

    if (sleeves != SleeveMode.none) {
      _paintSleeve(canvas, g.screenLeftArm, image, s, paint, left: true);
      _paintSleeve(canvas, g.screenRightArm, image, s, paint, left: false);
    }

    canvas.save();
    canvas.translate(g.shoulderMid.x, g.shoulderMid.y);
    canvas.rotate(g.angle);
    canvas.scale(s);
    canvas.translate(-w / 2, -h * _shoulderY);
    if (sleeves != SleeveMode.none) {
      final bottom = _sleeveBottom * h;
      final clip = Path()
        ..fillType = PathFillType.evenOdd
        ..addRect(Rect.fromLTWH(0, 0, w, h))
        ..addRect(Rect.fromLTWH(0, 0, w * _shoulderX, bottom))
        ..addRect(Rect.fromLTWH(w * (1 - _shoulderX), 0, w * _shoulderX, bottom));
      canvas.clipPath(clip);
    }
    canvas.drawImage(image, Offset.zero, paint);
    canvas.restore();
  }

  double get _sleeveBottom =>
      sleeves == SleeveMode.long ? _longSleeveBottom : _shortSleeveBottom;

  void _paintSleeve(
    Canvas canvas,
    ArmGeometry arm,
    ui.Image image,
    double s,
    Paint paint, {
    required bool left,
  }) {
    final w = image.width.toDouble();
    final h = image.height.toDouble();
    final stripWidth = w * _shoulderX;
    final stripX = left ? 0.0 : w * (1 - _shoulderX);
    // La manga de la foto cuelga hacia abajo y un poco hacia afuera; se rota
    // solo la diferencia entre esa posición de reposo y el brazo real.
    final rest = math.pi / 2 + (left ? _restSpread : -_restSpread);
    final anchorX = left ? stripWidth : 0.0;

    if (sleeves == SleeveMode.long) {
      final upperBottom = h * _elbowY;
      _drawStrip(
        canvas,
        image,
        paint,
        anchor: arm.upper.start,
        rotation: arm.upper.angle - rest,
        scale: s,
        src: Rect.fromLTWH(stripX, 0, stripWidth, upperBottom),
        offset: Offset(-anchorX, -h * _shoulderY),
      );
      _drawStrip(
        canvas,
        image,
        paint,
        anchor: arm.lower.start,
        rotation: arm.lower.angle - rest,
        scale: s,
        src: Rect.fromLTWH(
          stripX,
          upperBottom,
          stripWidth,
          h * (_longSleeveBottom - _elbowY),
        ),
        offset: Offset(-stripWidth / 2, 0),
      );
      return;
    }
    _drawStrip(
      canvas,
      image,
      paint,
      anchor: arm.upper.start,
      rotation: arm.upper.angle - rest,
      scale: s,
      src: Rect.fromLTWH(stripX, 0, stripWidth, h * _shortSleeveBottom),
      offset: Offset(-anchorX, -h * _shoulderY),
    );
  }

  void _drawStrip(
    Canvas canvas,
    ui.Image image,
    Paint paint, {
    required math.Point<double> anchor,
    required double rotation,
    required double scale,
    required Rect src,
    required Offset offset,
  }) {
    canvas.save();
    canvas.translate(anchor.x, anchor.y);
    canvas.rotate(rotation);
    canvas.scale(scale);
    canvas.drawImageRect(
      image,
      src,
      Rect.fromLTWH(offset.dx, offset.dy, src.width, src.height),
      paint,
    );
    canvas.restore();
  }

  // ------------------------------------------------------------ vector

  void _paintVector(Canvas canvas, GarmentGeometry g) {
    final sw = g.shoulderWidth;
    final color = fallbackColor;
    final dark = Color.lerp(color, Colors.black, .25)!;
    final downX = -math.sin(g.angle);
    final downY = math.cos(g.angle);
    Offset down(double k) => Offset(downX * sw * k, downY * sw * k);

    canvas.saveLayer(null, Paint());
    if (sleeves != SleeveMode.none) {
      final stroke = Paint()
        ..color = color
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round
        ..strokeWidth = sw * .34
        ..style = PaintingStyle.stroke;
      for (final arm in [g.leftArm, g.rightArm]) {
        final start = _o(arm.upper.start) + down(.12);
        final elbow = _o(arm.upper.end);
        final path = Path()..moveTo(start.dx, start.dy);
        if (sleeves == SleeveMode.long) {
          final wrist = _o(arm.lower.end);
          path
            ..lineTo(elbow.dx, elbow.dy)
            ..lineTo(wrist.dx, wrist.dy);
        } else {
          final end = Offset.lerp(start, elbow, .6)!;
          path.lineTo(end.dx, end.dy);
        }
        canvas.drawPath(path, stroke);
      }
    }

    final across = Offset(math.cos(g.angle), math.sin(g.angle)) * sw;
    final k = sleeves == SleeveMode.none ? .12 : .22;
    final ls = _o(g.screenLeftShoulder);
    final rs = _o(g.screenRightShoulder);
    final lh = _o(g.leftShoulder.x <= g.rightShoulder.x
        ? _hip(g, true)
        : _hip(g, false));
    final rh = _o(g.leftShoulder.x <= g.rightShoulder.x
        ? _hip(g, false)
        : _hip(g, true));
    final hem = down(.18);
    final body = Path()
      ..moveTo(
        ls.dx - across.dx * k - down(.06).dx,
        ls.dy - across.dy * k - down(.06).dy,
      )
      ..lineTo(
        lh.dx - across.dx * k * 1.15 + hem.dx,
        lh.dy - across.dy * k * 1.15 + hem.dy,
      )
      ..lineTo(
        rh.dx + across.dx * k * 1.15 + hem.dx,
        rh.dy + across.dy * k * 1.15 + hem.dy,
      )
      ..lineTo(
        rs.dx + across.dx * k - down(.06).dx,
        rs.dy + across.dy * k - down(.06).dy,
      )
      ..close();
    canvas.drawPath(body, Paint()..color = color);
    canvas.drawPath(
      body,
      Paint()
        ..color = dark
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );

    // Cuello: se recorta para que se vea la piel.
    final neck = _o(g.shoulderMid) + down(.05);
    canvas.save();
    canvas.translate(neck.dx, neck.dy);
    canvas.rotate(g.angle);
    canvas.drawOval(
      Rect.fromCenter(center: Offset.zero, width: sw * .36, height: sw * .22),
      Paint()..blendMode = BlendMode.clear,
    );
    canvas.restore();
    canvas.restore();
  }

  math.Point<double> _hip(GarmentGeometry g, bool left) {
    // Las caderas no están en GarmentGeometry por lado; se reconstruyen desde
    // hipMid manteniendo la anchura de hombros reducida.
    final acrossX = math.cos(g.angle) * g.shoulderWidth * .42;
    final acrossY = math.sin(g.angle) * g.shoulderWidth * .42;
    return left
        ? math.Point(g.hipMid.x - acrossX, g.hipMid.y - acrossY)
        : math.Point(g.hipMid.x + acrossX, g.hipMid.y + acrossY);
  }

  static Offset _o(math.Point<double> p) => Offset(p.x, p.y);

  // ------------------------------------------------------------ puntos

  void _paintPoints(Canvas canvas, BodyPose pose, PreviewMapper mapper) {
    final bone = Paint()
      ..color = const Color(0xFF00E5FF)
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    for (final (a, b) in skeletonBones) {
      final pa = pose.points[a];
      final pb = pose.points[b];
      if (pa == null || pb == null) continue;
      canvas.drawLine(mapper.map(pa.x, pa.y), mapper.map(pb.x, pb.y), bone);
    }
    final seen = Paint()..color = const Color(0xFFFFEA00);
    final guessed = Paint()..color = const Color(0xFFFF7043);
    pose.points.forEach((joint, point) {
      if (joint.index < BodyJoint.leftShoulder.index) return;
      final estimated = pose.estimated.contains(joint);
      canvas.drawCircle(
        mapper.map(point.x, point.y),
        estimated ? 5 : 6,
        estimated ? guessed : seen,
      );
    });
  }

  @override
  bool shouldRepaint(GarmentPainter old) =>
      old.pose != pose ||
      old.garment != garment ||
      old.showPoints != showPoints ||
      old.showGarment != showGarment ||
      old.previewSize != previewSize ||
      old.scale != scale ||
      old.sleeves != sleeves ||
      old.fallbackColor != fallbackColor;
}
