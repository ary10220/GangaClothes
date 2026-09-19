import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/theme.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/auth/session_model.dart';
import 'package:mobile/features/cart/cart_controller.dart';
import 'package:mobile/features/cart/cart_models.dart';
import 'package:mobile/features/cart/cart_screen.dart';
import 'package:mobile/features/cart/cart_service.dart';
import 'package:mobile/features/cart/payment_sheet.dart';

void main() {
  testWidgets('shows insufficient stock and disables payment', (tester) async {
    final controller = CartController(api: _FakeCartApi());
    await tester.pumpWidget(
      MaterialApp(
        theme: GangaTheme.light(),
        home: CartScreen(
          apiClient: ApiClient(),
          session: const Session(
            accessToken: 'token',
            user: User(
              id: 1,
              name: 'Cliente',
              email: 'c@example.com',
              roles: ['cliente'],
            ),
          ),
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Stock insuficiente'), findsOneWidget);
    final payment = find.widgetWithText(FilledButton, 'Pagar Bs 80,00');
    expect(payment, findsOneWidget);
    final button = tester.widget<FilledButton>(payment);
    expect(button.onPressed, isNull);
  });

  testWidgets('validates test payment fields without sending card data', (
    tester,
  ) async {
    expect(validateCardNumber('4242 4242 4242 4242'), isNull);
    expect(validateCardNumber('4242'), isNotNull);
    expect(validateCardHolder('  '), isNotNull);
    expect(validateCardExpiry('12/30', now: DateTime(2026, 1)), isNull);
    expect(validateCardExpiry('01/26', now: DateTime(2026, 1)), isNotNull);
    expect(validateCvc('123'), isNull);
    expect(validateCvc('12'), isNotNull);
  });
}

class _FakeCartApi implements CartDataSource {
  @override
  Future<Cart?> fetchCart() async => _cart;

  @override
  Future<List<CartBranch>> fetchBranches() async => const [
    CartBranch(id: 2, name: 'Centro', active: true),
  ];

  @override
  Future<Cart> changeBranch(int branchId) async => _cart;

  @override
  Future<Cart> updateQuantity({
    required int lineId,
    required int quantity,
  }) async => _cart;

  @override
  Future<Cart> removeLine(int lineId) async => _cart;

  @override
  Future<Cart> confirmCart() async => _cart;

  @override
  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required bool simulateFailure,
  }) async => throw UnimplementedError();
}

final _cart = Cart(
  id: 4,
  status: 'carrito',
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
      available: 0,
      reaches: false,
    ),
  ],
);
