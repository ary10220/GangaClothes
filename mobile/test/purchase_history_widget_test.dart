import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/theme.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/auth/session_model.dart';
import 'package:mobile/features/purchase_history/purchase_history_models.dart';
import 'package:mobile/features/purchase_history/purchase_history_screen.dart';
import 'package:mobile/features/purchase_history/purchase_history_service.dart';

void main() {
  testWidgets('renders receipt, payment, details, and totals', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: gangaTheme(),
        home: PurchaseHistoryScreen(
          purchaseHistoryService: _FakePurchaseSource(),
          session: _session,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('FAC-12'), findsOneWidget);
    expect(find.text('Camisa · M · Azul'), findsOneWidget);
    expect(find.text('Pago: Tarjeta / pasarela · aprobado'), findsOneWidget);
    expect(find.text('Descuento'), findsOneWidget);
    expect(find.text('Total'), findsOneWidget);
    expect(find.text('Bs 170,50'), findsOneWidget);
  });

  testWidgets('shows the empty state and the catalog action', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: gangaTheme(),
        home: PurchaseHistoryScreen(
          purchaseHistoryService: _FakePurchaseSource(items: const []),
          session: _session,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Todavia no tienes compras pagadas.'), findsOneWidget);
    expect(find.text('Ir al catalogo'), findsOneWidget);
  });

  testWidgets('shows an API error and retries the purchase history', (
    tester,
  ) async {
    final source = _FakePurchaseSource(failFirstRequest: true);
    await tester.pumpWidget(
      MaterialApp(
        theme: gangaTheme(),
        home: PurchaseHistoryScreen(
          purchaseHistoryService: source,
          session: _session,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('No se pudo cargar el historial.'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);

    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();

    expect(find.text('FAC-12'), findsOneWidget);
  });
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

class _FakePurchaseSource implements PurchaseHistoryDataSource {
  _FakePurchaseSource({List<Purchase>? items, this.failFirstRequest = false})
    : items = items ?? [_purchase];

  final List<Purchase> items;
  final bool failFirstRequest;
  int requestCount = 0;

  @override
  Future<List<Purchase>> fetchPurchases() async {
    if (failFirstRequest && requestCount++ == 0) {
      throw const ApiError(
        statusCode: 503,
        message: 'No se pudo cargar el historial.',
      );
    }
    return items;
  }
}

final _purchase = Purchase(
  id: 12,
  status: 'pagada',
  channel: 'web',
  dateRaw: '2030-04-05T09:07:06Z',
  branchId: 2,
  branchName: 'Centro',
  customer: null,
  cashier: null,
  reservationId: null,
  units: 2,
  subtotal: 180.5,
  discount: 10,
  total: 170.5,
  receiptNumber: 'FAC-12',
  details: const [
    PurchaseDetail(
      id: 3,
      variantId: 4,
      sku: 'CAM-04',
      garment: 'Camisa',
      size: 'M',
      color: 'Azul',
      quantity: 2,
      unitPrice: 90.25,
      subtotal: 180.5,
    ),
  ],
  payments: const [
    PurchasePayment(
      id: 2,
      method: 'pasarela',
      amount: 170.5,
      status: 'exitoso',
      externalReference: 'ref-2',
    ),
  ],
);
