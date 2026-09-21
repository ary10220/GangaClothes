import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/shipment_tracking/shipment_controller.dart';
import 'package:mobile/features/shipment_tracking/shipment_models.dart';
import 'package:mobile/features/shipment_tracking/shipment_service.dart';

void main() {
  test(
    'starts polling only for active shipments and stops at a terminal response',
    () async {
      final api = _FakeShipmentSource([
        [_shipment(active: true, state: ShipmentState.pending)],
        [_shipment(active: false, state: ShipmentState.delivered)],
      ]);
      final controller = ShipmentTrackingController(
        api: api,
        pollInterval: const Duration(hours: 1),
      );

      await controller.load();
      expect(controller.polling, isTrue);
      await controller.poll();
      expect(controller.polling, isFalse);
      expect(controller.shipments.single.state, ShipmentState.delivered);
      controller.dispose();
    },
  );

  test('keeps the last state and retries after a polling failure', () async {
    final api = _FakeShipmentSource([
      [_shipment(active: true, state: ShipmentState.assigned)],
      const ApiError(statusCode: 503, message: 'Servidor ocupado'),
      [_shipment(active: false, state: ShipmentState.cancelled)],
    ]);
    final controller = ShipmentTrackingController(
      api: api,
      pollInterval: const Duration(hours: 1),
    );

    await controller.load();
    await controller.poll();
    expect(controller.shipments.single.state, ShipmentState.assigned);
    expect(controller.error?.statusCode, 503);
    expect(controller.polling, isTrue);

    await controller.poll();
    expect(controller.error, isNull);
    expect(controller.polling, isFalse);
    controller.dispose();
  });

  test(
    'uses the fifteen-second production interval and cancels it on dispose',
    () async {
      final api = _FakeShipmentSource([
        [_shipment(active: true, state: ShipmentState.pending)],
      ]);
      final controller = ShipmentTrackingController(api: api);

      expect(controller.pollInterval, const Duration(seconds: 15));
      await controller.load();
      expect(controller.polling, isTrue);
      controller.dispose();
      await Future<void>.delayed(const Duration(milliseconds: 1));
      expect(api.calls, 1);
    },
  );
}

class _FakeShipmentSource implements ShipmentDataSource {
  _FakeShipmentSource(this.responses);

  final List<Object> responses;
  int calls = 0;

  @override
  Future<List<Shipment>> fetchShipments() async {
    final response =
        responses[calls < responses.length ? calls : responses.length - 1];
    calls++;
    if (response is! List<Shipment>) {
      throw response;
    }
    return response;
  }
}

Shipment _shipment({required bool active, required String state}) =>
    Shipment(id: 1, state: state, stateLabel: state, active: active);
