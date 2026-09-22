import 'dart:math' as math;

import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/virtual_fitting/body_model.dart';

Map<BodyJoint, BodyPoint> _upright({double likelihood = .9}) => {
  // Buffer 640x480 rotado 90°: el marco vertical mide 480x640.
  BodyJoint.leftShoulder: BodyPoint(336, 192, likelihood),
  BodyJoint.rightShoulder: BodyPoint(144, 192, likelihood),
  BodyJoint.leftElbow: BodyPoint(380, 320, likelihood),
  BodyJoint.rightElbow: BodyPoint(100, 320, likelihood),
  BodyJoint.leftWrist: BodyPoint(400, 440, likelihood),
  BodyJoint.rightWrist: BodyPoint(80, 440, likelihood),
  BodyJoint.leftHip: BodyPoint(300, 448, likelihood),
  BodyJoint.rightHip: BodyPoint(180, 448, likelihood),
};

BodyPose _pose({
  Map<BodyJoint, BodyPoint>? raw,
  bool mirror = false,
  int rotation = 90,
}) => BodyPose.fromLandmarks(
  raw: raw ?? _upright(),
  imageWidth: 640,
  imageHeight: 480,
  rotationDegrees: rotation,
  mirror: mirror,
)!;

void main() {
  group('BodyPose.fromLandmarks', () {
    test('normaliza con el ancho y alto intercambiados al rotar 90°', () {
      final pose = _pose();
      expect(pose[BodyJoint.leftShoulder].x, closeTo(.7, .001));
      expect(pose[BodyJoint.leftShoulder].y, closeTo(.3, .001));
      expect(pose[BodyJoint.rightHip].x, closeTo(.375, .001));
      expect(pose.estimated, isEmpty);
    });

    test('espeja solo el eje x', () {
      final pose = _pose(mirror: true);
      expect(pose[BodyJoint.leftShoulder].x, closeTo(.3, .001));
      expect(pose[BodyJoint.rightShoulder].x, closeTo(.7, .001));
      expect(pose[BodyJoint.leftShoulder].y, closeTo(.3, .001));
    });

    test('sin rotación usa el ancho y alto originales', () {
      final pose = _pose(
        rotation: 0,
        raw: {
          BodyJoint.leftShoulder: const BodyPoint(448, 144, .9),
          BodyJoint.rightShoulder: const BodyPoint(192, 144, .9),
        },
      );
      expect(pose[BodyJoint.leftShoulder].x, closeTo(.7, .001));
      expect(pose[BodyJoint.leftShoulder].y, closeTo(.3, .001));
    });

    test('rechaza la pose si un hombro no es confiable', () {
      final raw = _upright();
      raw[BodyJoint.leftShoulder] = const BodyPoint(336, 192, .2);
      expect(
        BodyPose.fromLandmarks(
          raw: raw,
          imageWidth: 640,
          imageHeight: 480,
          rotationDegrees: 90,
          mirror: false,
        ),
        isNull,
      );
    });

    test('estima caderas, codos y muñecas cuando faltan', () {
      final pose = _pose(
        raw: {
          BodyJoint.leftShoulder: const BodyPoint(336, 192, .9),
          BodyJoint.rightShoulder: const BodyPoint(144, 192, .9),
          BodyJoint.leftHip: const BodyPoint(300, 448, .1),
        },
      );
      expect(
        pose.estimated,
        containsAll([
          BodyJoint.leftHip,
          BodyJoint.rightHip,
          BodyJoint.leftElbow,
          BodyJoint.rightElbow,
          BodyJoint.leftWrist,
          BodyJoint.rightWrist,
        ]),
      );
      // Las caderas estimadas quedan debajo de los hombros y algo más juntas.
      final ls = pose[BodyJoint.leftShoulder];
      final lh = pose[BodyJoint.leftHip];
      expect(lh.y, greaterThan(ls.y));
      expect(lh.x, lessThan(ls.x));
      final lw = pose[BodyJoint.leftWrist];
      expect(lw.y, greaterThan(pose[BodyJoint.leftElbow].y));
    });

    test(
      'mantiene puntos fuera de cuadro (una muñeca fuera sigue dando dirección)',
      () {
        final raw = _upright();
        raw[BodyJoint.leftWrist] = const BodyPoint(520, 700, .9);
        final pose = _pose(raw: raw);
        expect(pose[BodyJoint.leftWrist].x, greaterThan(1));
        expect(pose.estimated, isNot(contains(BodyJoint.leftWrist)));
      },
    );
  });

  group('BodyTracker', () {
    test('suaviza entre frames y olvida el cuerpo tras 1.2 s sin pose', () {
      var now = DateTime(2026, 1, 1, 12);
      final tracker = BodyTracker(now: () => now);

      expect(tracker.update(_pose()), isTrue);
      expect(tracker.pose![BodyJoint.leftShoulder].x, closeTo(.7, .001));

      final moved = _upright();
      moved[BodyJoint.leftShoulder] = const BodyPoint(384, 192, .9); // x=.8
      now = now.add(const Duration(milliseconds: 100));
      tracker.update(_pose(raw: moved));
      expect(tracker.pose![BodyJoint.leftShoulder].x, closeTo(.75, .001));

      now = now.add(const Duration(milliseconds: 500));
      expect(tracker.update(null), isFalse);
      expect(tracker.pose, isNotNull);

      now = now.add(const Duration(milliseconds: 800));
      expect(tracker.update(null), isTrue);
      expect(tracker.pose, isNull);
    });
  });

  group('GarmentGeometry', () {
    math.Point<double> map(BodyPoint p) => math.Point(p.x * 400, p.y * 800);

    test(
      'mide hombros y torso en píxeles y calcula el ángulo de cada brazo',
      () {
        final g = GarmentGeometry.compute(_pose(), map);
        expect(g.shoulderWidth, closeTo(160, .5));
        expect(g.shoulderMid.x, closeTo(200, .5));
        expect(g.angle, closeTo(0, .001));
        expect(g.torsoLength, closeTo(320, .5));
        // Brazo izquierdo hacia abajo y afuera (x crece, y crece).
        expect(g.leftArm.upper.angle, greaterThan(0));
        expect(g.leftArm.upper.angle, lessThan(math.pi / 2));
        expect(g.leftArm.upper.estimated, isFalse);
      },
    );

    test('la manga sigue al codo cuando el brazo se levanta', () {
      final raised = _upright();
      raised[BodyJoint.leftElbow] = const BodyPoint(420, 100, .9);
      final g = GarmentGeometry.compute(_pose(raw: raised), map);
      expect(g.leftArm.upper.angle, lessThan(0));
    });

    test('el ángulo del torso nunca da la vuelta aunque se espeje', () {
      final tilted = _upright();
      tilted[BodyJoint.leftShoulder] = const BodyPoint(336, 230, .9);
      final normal = GarmentGeometry.compute(_pose(raw: tilted), map);
      final mirrored = GarmentGeometry.compute(
        _pose(raw: tilted, mirror: true),
        map,
      );
      expect(normal.angle.abs(), lessThan(math.pi / 2));
      expect(mirrored.angle, closeTo(-normal.angle, .001));
      expect(
        mirrored.screenLeftShoulder.x,
        lessThan(mirrored.screenRightShoulder.x),
      );
    });
  });

  test('sleeveModeFor deduce la manga por el nombre', () {
    expect(sleeveModeFor('Polera basica algodon'), SleeveMode.short);
    expect(sleeveModeFor('Camisa denim estampada'), SleeveMode.long);
    expect(sleeveModeFor('Chamarra bomber terracota'), SleeveMode.long);
    expect(sleeveModeFor('Vestido floral rojo'), SleeveMode.none);
    expect(sleeveModeFor('Pantalon jogger rosa palo'), SleeveMode.none);
  });
}
