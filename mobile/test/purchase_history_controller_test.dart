import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/purchase_history/purchase_history_controller.dart';
import 'package:mobile/features/purchase_history/purchase_history_models.dart';
import 'package:mobile/features/purchase_history/purchase_history_service.dart';

void main() {
  test('loads purchases and clears a previous error', () async {
    final api = _FakePurchaseSource();
    final controller = PurchaseHistoryController(api: api);

    await controller.load();

    expect(controller.loading, isFalse);
    expect(controller.error, isNull);
    expect(controller.purchases.single.id, 1);
  });

  test('normalizes an API failure for the retry panel', () async {
    final api = _FakePurchaseSource()..failure = true;
    final controller = PurchaseHistoryController(api: api);

    await controller.load();

    expect(controller.loading, isFalse);
    expect(controller.error?.message, 'No se pudo cargar el historial.');
    expect(controller.purchases, isEmpty);
  });

  test('loads a JSON receipt through the existing controller', () async {
    final controller = PurchaseHistoryController(
      api: _FakePurchaseSource(),
      receiptApi: _FakeReceiptSource(),
    );

    final receipt = await controller.loadReceipt(1);

    expect(receipt?.receiptNumber, 'FAC-1');
    expect(controller.receiptError, isNull);
    expect(controller.receiptPurchaseId, 1);
  });

  test('normalizes a receipt error for the customer action', () async {
    final controller = PurchaseHistoryController(
      api: _FakePurchaseSource(),
      receiptApi: _FakeReceiptSource()..failure = true,
    );

    final receipt = await controller.loadReceipt(1);

    expect(receipt, isNull);
    expect(
      controller.receiptError?.message,
      'No se pudo cargar el comprobante.',
    );
    expect(controller.receiptLoading, isFalse);
  });
}

class _FakePurchaseSource implements PurchaseHistoryDataSource {
  bool failure = false;

  @override
  Future<List<Purchase>> fetchPurchases() async {
    if (failure) {
      throw const ApiError(
        statusCode: 503,
        message: 'No se pudo cargar el historial.',
      );
    }
    return [
      Purchase(
        id: 1,
        status: 'pagada',
        channel: 'web',
        dateRaw: null,
        branchId: 2,
        branchName: 'Centro',
        customer: null,
        cashier: null,
        reservationId: null,
        units: 1,
        subtotal: 80,
        discount: 0,
        total: 80,
        receiptNumber: null,
        details: const [],
        payments: const [],
      ),
    ];
  }
}

class _FakeReceiptSource implements PurchaseReceiptDataSource {
  bool failure = false;

  @override
  Future<PurchaseReceipt> fetchReceipt(int purchaseId) async {
    if (failure) throw StateError('receipt failed');
    return const PurchaseReceipt(
      receiptNumber: 'FAC-1',
      dateRaw: null,
      items: [],
      subtotal: 80,
      discount: 0,
      shippingCost: 0,
      delivery: null,
      total: 80,
      currency: 'BOB',
      payment: null,
    );
  }
}
