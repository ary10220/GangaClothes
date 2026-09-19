import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/reservations/reservation_controller.dart';
import 'package:mobile/features/reservations/reservation_models.dart';
import 'package:mobile/features/reservations/reservation_service.dart';

void main() {
  test(
    'defaults to active reservations and counts all statuses locally',
    () async {
      final api = _FakeReservationDataSource(_reservations());
      final controller = ReservationController(api: api);

      await controller.load();

      expect(controller.filter, ReservationFilter.active);
      expect(controller.activeCount, 2);
      expect(controller.allCount, 5);
      expect(controller.visibleReservations.map((item) => item.status), [
        ReservationStatus.pending,
        ReservationStatus.prepared,
      ]);
    },
  );

  test('keeps every backend status and its customer explanation', () {
    expect(ReservationStatus.all, hasLength(5));
    expect(
      ReservationStatus.all.map(ReservationStatus.explanation),
      containsAll(<String>[
        'La sucursal recibio tu reserva y va a preparar las prendas.',
        'Tus prendas te esperan en el vestidor.',
        'Ya pasaste por la tienda a probartelas.',
        'Cancelaste esta reserva; las prendas volvieron a estar disponibles.',
        'No llegaste a la cita y las prendas se liberaron.',
      ]),
    );
    expect(
      isOverdueActive(
        _reservation(1, ReservationStatus.pending),
        now: DateTime(2030, 4, 6, 11),
      ),
      isTrue,
    );
  });

  test(
    'replaces the card with the returned reservation after cancellation',
    () async {
      final updated = _reservation(1, ReservationStatus.cancelled);
      final api = _FakeReservationDataSource(_reservations(), updated: updated);
      final controller = ReservationController(api: api);
      await controller.load();

      controller.setConfirmation(1);
      await controller.cancel(controller.reservations.first);

      expect(controller.reservations.first.status, ReservationStatus.cancelled);
      expect(controller.feedback, contains('Reserva #R-1 cancelada'));
      expect(controller.confirmingId, isNull);
    },
  );

  test('shows cancellation error and reloads the reservation list', () async {
    final api = _FakeReservationDataSource(_reservations())
      ..failCancellation = true;
    final controller = ReservationController(api: api);
    await controller.load();
    await controller.cancel(controller.reservations.first);

    expect(api.fetchCount, 2);
    expect(controller.feedback, 'No se pudo cancelar la reserva.');
    expect(controller.cancellingId, isNull);
  });
}

class _FakeReservationDataSource implements ReservationDataSource {
  _FakeReservationDataSource(this.items, {this.updated});

  List<Reservation> items;
  final Reservation? updated;
  bool failCancellation = false;
  int fetchCount = 0;

  @override
  Future<List<Reservation>> fetchReservations() async {
    fetchCount++;
    return items;
  }

  @override
  Future<Reservation> cancelReservation(int reservationId) async {
    if (failCancellation) {
      throw const ApiError(
        statusCode: 400,
        message: 'No se pudo cancelar la reserva.',
      );
    }
    return updated!;
  }
}

List<Reservation> _reservations() => [
  _reservation(1, ReservationStatus.pending),
  _reservation(2, ReservationStatus.prepared),
  _reservation(3, ReservationStatus.attended),
  _reservation(4, ReservationStatus.cancelled),
  _reservation(5, ReservationStatus.expired),
];

Reservation _reservation(int id, String status) => Reservation(
  id: id,
  status: status,
  createdAtRaw: '2030-04-05T09:07:06Z',
  appointmentRaw: '2030-04-06T10:30:00',
  notes: null,
  branch: 'Centro',
  units: 1,
  details: const [],
);
