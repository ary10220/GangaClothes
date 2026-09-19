import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/cart/cart_controller.dart';
import 'package:mobile/features/cart/cart_models.dart';
import 'package:mobile/features/cart/cart_service.dart';

void main() {
  test('blocks payment when a line does not reach stock', () async {
    final api = _FakeCartApi(cart: _cart(reaches: false));
    final controller = CartController(api: api);

    await controller.load();
    expect(controller.canPay, isFalse);
    expect(api.confirmCalls, 0);
  });

  test('confirms once, then retries payment without reconfirming', () async {
    final api = _FakeCartApi(
      cart: _cart(),
      paymentError: const ApiError(
        statusCode: 503,
        message: 'Servidor ocupado',
      ),
    );
    final controller = CartController(api: api);
    await controller.load();

    expect(await controller.checkout(simulateFailure: false), isNull);
    expect(api.confirmCalls, 1);
    expect(controller.pendingSale, isNotNull);
    expect(controller.paymentError, contains('pendiente'));

    api.paymentError = null;
    final receipt = await controller.checkout(simulateFailure: false);
    expect(receipt?.approved, isTrue);
    expect(api.confirmCalls, 1);
    expect(api.paymentCalls, 2);
    expect(controller.receipt?.receiptNumber, 'C-000001');
  });

  test('402 clears pending sale, reloads cart, and exposes motivo', () async {
    final api = _FakeCartApi(
      cart: _cart(),
      paymentError: const ApiError(
        statusCode: 402,
        message: 'El pago fue rechazado.',
        details: {'motivo': 'Card declined (simulado)'},
      ),
    );
    final controller = CartController(api: api);
    await controller.load();

    await controller.checkout(simulateFailure: true);

    expect(controller.pendingSale, isNull);
    expect(controller.paymentError, contains('Card declined (simulado).'));
    expect(api.fetchCartCalls, greaterThan(1));
  });
}

class _FakeCartApi implements CartDataSource {
  _FakeCartApi({this.cart, this.paymentError});

  Cart? cart;
  ApiError? paymentError;
  int fetchCartCalls = 0;
  int confirmCalls = 0;
  int paymentCalls = 0;

  @override
  Future<Cart?> fetchCart() async {
    fetchCartCalls++;
    return cart;
  }

  @override
  Future<List<CartBranch>> fetchBranches() async => const [
    CartBranch(id: 2, name: 'Centro', active: true),
  ];

  @override
  Future<Cart> changeBranch(int branchId) async => cart!;

  @override
  Future<Cart> updateQuantity({
    required int lineId,
    required int quantity,
  }) async => cart!;

  @override
  Future<Cart> removeLine(int lineId) async => cart!;

  @override
  Future<Cart> confirmCart() async {
    confirmCalls++;
    return cart!;
  }

  @override
  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required bool simulateFailure,
  }) async {
    paymentCalls++;
    if (paymentError != null) throw paymentError!;
    return PaymentResult(
      approved: true,
      receiptNumber: 'C-000001',
      externalReference: 'pi_test_1',
      sale: _cart(status: 'pagada'),
    );
  }
}

Cart _cart({bool reaches = true, String status = 'carrito'}) => Cart(
  id: 4,
  status: status,
  branchId: 2,
  branchName: 'Centro',
  units: 1,
  subtotal: 80,
  discount: 0,
  total: 80,
  receiptNumber: null,
  lines: [
    CartLine(
      id: 8,
      variantId: 9,
      sku: 'GC-09',
      garment: 'Camisa',
      size: 'M',
      color: 'Azul',
      quantity: 1,
      unitPrice: 80,
      subtotal: 80,
      available: reaches ? 2 : 0,
      reaches: reaches,
    ),
  ],
);
