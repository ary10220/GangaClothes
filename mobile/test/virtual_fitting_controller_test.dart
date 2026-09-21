import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/virtual_fitting/pose_placement_controller.dart';

void main() {
  test('computes an automatic torso rectangle from shoulders and hips', () {
    final controller = PosePlacementController();

    expect(
      controller.update(
        const TorsoLandmarks(
          leftShoulder: PosePoint(.3, .3),
          rightShoulder: PosePoint(.7, .3),
          leftHip: PosePoint(.37, .7),
          rightHip: PosePoint(.63, .7),
        ),
      ),
      isTrue,
    );

    final placement = controller.placement!;
    expect(placement.left, closeTo(.18, .02));
    expect(placement.top, closeTo(.24, .02));
    expect(placement.width, greaterThan(.4));
    expect(placement.height, greaterThan(.5));
  });

  test(
    'keeps the last valid placement when landmarks are missing or invalid',
    () {
      final controller = PosePlacementController();
      const valid = TorsoLandmarks(
        leftShoulder: PosePoint(.3, .3),
        rightShoulder: PosePoint(.7, .3),
        leftHip: PosePoint(.37, .7),
        rightHip: PosePoint(.63, .7),
      );
      controller.update(valid);
      final previous = controller.placement;

      expect(
        controller.update(
          const TorsoLandmarks(
            leftShoulder: PosePoint(.3, .3),
            rightShoulder: PosePoint(.7, .3),
            leftHip: PosePoint(.4, .3),
            rightHip: PosePoint(.6, .3),
          ),
        ),
        isFalse,
      );
      expect(controller.placement, same(previous));

      expect(
        controller.update(
          const TorsoLandmarks(
            leftShoulder: PosePoint(double.nan, .3),
            rightShoulder: PosePoint(.7, .3),
            leftHip: PosePoint(.37, .7),
            rightHip: PosePoint(.63, .7),
          ),
        ),
        isFalse,
      );
      expect(controller.placement, same(previous));
    },
  );

  test('does not create a placement without a previous valid pose', () {
    final controller = PosePlacementController();
    expect(
      controller.update(
        const TorsoLandmarks(
          leftShoulder: PosePoint(.3, .3),
          rightShoulder: PosePoint(.31, .3),
          leftHip: PosePoint(.4, .7),
          rightHip: PosePoint(.41, .7),
        ),
      ),
      isFalse,
    );
    expect(controller.placement, isNull);
  });
}
