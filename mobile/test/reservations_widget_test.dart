import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/theme.dart';
import 'package:mobile/features/auth/session_model.dart';
import 'package:mobile/features/reservations/reservation_models.dart';
import 'package:mobile/features/reservations/reservation_service.dart';
import 'package:mobile/features/reservations/reservations_screen.dart';

void main() {
  testWidgets(
    'renders reservation cards and requires cancellation confirmation',
    (tester) async {
      final api = _FakeReservationDataSource();
      await tester.pumpWidget(
        MaterialApp(
          theme: gangaTheme(),
          home: ReservationsScreen(
            reservationService: api,
            session: const Session(
              accessToken: 'token',
              user: User(
                id: 1,
                name: 'Cliente',
                email: 'cliente@example.com',
                roles: ['cliente'],
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('#R-1'), findsOneWidget);
      expect(find.text('Camisa · M · Azul'), findsOneWidget);
      expect(find.text('×2'), findsOneWidget);
      expect(
        find.text(
          'La sucursal recibio tu reserva y va a preparar las prendas.',
        ),
        findsOneWidget,
      );
      expect(find.text('Cancelar reserva'), findsOneWidget);

      await tester.tap(find.text('Cancelar reserva'));
      await tester.pump();
      expect(find.text('¿Cancelar la reserva?'), findsOneWidget);
      expect(find.text('Sí, cancelar'), findsOneWidget);
      expect(api.cancelledId, isNull);
    },
  );
}

class _FakeReservationDataSource implements ReservationDataSource {
  int? cancelledId;

  @override
  Future<List<Reservation>> fetchReservations() async => [
    Reservation(
      id: 1,
      status: ReservationStatus.pending,
      createdAtRaw: '2030-04-05T09:07:06Z',
      appointmentRaw: '2030-04-06T10:30:00',
      notes: 'Probador',
      branch: 'Centro',
      units: 2,
      details: const [
        ReservationDetail(
          id: 9,
          variantId: 3,
          sku: 'CAM-03',
          garment: 'Camisa',
          size: 'M',
          color: 'Azul',
          quantity: 2,
        ),
      ],
    ),
  ];

  @override
  Future<Reservation> cancelReservation(int reservationId) async {
    cancelledId = reservationId;
    return (await fetchReservations()).first;
  }
}
