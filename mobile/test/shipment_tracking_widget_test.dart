import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/theme.dart';
import 'package:mobile/features/auth/session_model.dart';
import 'package:mobile/features/shipment_tracking/shipment_models.dart';
import 'package:mobile/features/shipment_tracking/shipment_service.dart';
import 'package:mobile/features/shipment_tracking/shipment_tracking_screen.dart';

void main() {
  testWidgets(
    'renders the supplied summary, five-date timeline, and no-map limitation',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: gangaTheme(),
          home: ShipmentTrackingScreen(
            shipmentService: _FakeShipmentSource(),
            session: _session,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Envío #30'), findsOneWidget);
      expect(find.text('En camino'), findsOneWidget);
      expect(find.textContaining('El mapa no está disponible'), findsOneWidget);
      expect(find.textContaining('Origen (Centro)'), findsOneWidget);
      expect(find.textContaining('Repartidor: Alex'), findsOneWidget);
      expect(find.textContaining('Creación:'), findsOneWidget);
      expect(find.textContaining('Asignación:'), findsOneWidget);
      expect(find.textContaining('Salida:'), findsOneWidget);
      expect(find.textContaining('Entrega estimada:'), findsOneWidget);
      expect(find.textContaining('Entrega:'), findsOneWidget);
    },
  );
}

const _session = Session(
  accessToken: 'token',
  user: User(
    id: 1,
    name: 'Cliente',
    email: 'cliente@example.com',
    roles: ['cliente'],
  ),
);

class _FakeShipmentSource implements ShipmentDataSource {
  @override
  Future<List<Shipment>> fetchShipments() async => [
    Shipment(
      id: 30,
      state: ShipmentState.onTheWay,
      stateLabel: 'En camino',
      active: false,
      address: 'Av. Siempre Viva 123',
      latitude: -17.78,
      longitude: -63.18,
      express: true,
      driver: 'Alex',
      createdAt: DateTime.parse('2030-04-05T09:07:06Z').toLocal(),
      assignedAt: DateTime.parse('2030-04-05T09:17:06Z').toLocal(),
      departedAt: DateTime.parse('2030-04-05T09:27:06Z').toLocal(),
      estimatedAt: DateTime.parse('2030-04-05T10:07:06Z').toLocal(),
      deliveredAt: DateTime.parse('2030-04-05T10:00:06Z').toLocal(),
      origin: const ShipmentBranch(id: 2, name: 'Centro'),
      sale: const ShipmentSaleSummary(
        id: 12,
        state: 'pagada',
        channel: 'movil',
      ),
    ),
  ];
}
