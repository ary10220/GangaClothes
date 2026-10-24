import 'dart:typed_data';

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
import 'package:mobile/features/delivery/delivery_map.dart';
import 'package:mobile/features/delivery/delivery_models.dart';
import 'package:mobile/features/delivery/delivery_service.dart';
import 'package:mobile/features/purchase_history/purchase_history_models.dart';
import 'package:mobile/features/purchase_history/purchase_history_service.dart';

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
    expect(find.text('Retiro en sucursal'), findsOneWidget);
    final payment = find.widgetWithText(FilledButton, 'Pagar Bs 80,00');
    expect(payment, findsOneWidget);
    final button = tester.widget<FilledButton>(payment);
    expect(button.onPressed, isNull);
  });

  testWidgets('shows promotion and delivery summary from backend values', (
    tester,
  ) async {
    final controller = CartController(api: _FakeCartApi(cart: _deliveryCart));
    await tester.pumpWidget(
      MaterialApp(
        theme: GangaTheme.light(),
        home: CartScreen(
          apiClient: ApiClient(),
          session: null,
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('30% OFF'), findsOneWidget);
    expect(find.text('Precio unitario · Bs 72,35'), findsOneWidget);
    expect(find.text('Ahorrás Bs 17,65'), findsOneWidget);
    expect(find.text('Entrega a domicilio'), findsOneWidget);
    expect(find.text('Envío'), findsOneWidget);
    expect(find.text('Bs 6,50'), findsOneWidget);
    expect(find.text('Dirección: Av. Siempre Viva 123'), findsOneWidget);
    expect(find.text('Descuento'), findsOneWidget);
    expect(find.text('Pagar Bs 78,85'), findsOneWidget);
    expect(find.text('Bs 90,00'), findsOneWidget);
    expect(
      tester.widget<Text>(find.text('Bs 90,00')).style?.decoration,
      TextDecoration.lineThrough,
    );
  });

  testWidgets('delivery sheet shows the map picker, the fields and the quote', (
    tester,
  ) async {
    final controller = CartController(api: _FakeCartApi(cart: _deliveryCart));
    await tester.pumpWidget(
      MaterialApp(
        theme: GangaTheme.light(),
        home: CartScreen(
          apiClient: ApiClient(),
          session: null,
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView), const Offset(0, -500));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Editar entrega'));
    await tester.pumpAndSettle();

    expect(find.text('Dirección'), findsOneWidget);
    expect(find.text('Referencia (opcional)'), findsOneWidget);
    expect(find.text('Teléfono de contacto'), findsOneWidget);
    expect(find.byType(DeliveryMap), findsOneWidget);
    expect(find.textContaining('Ubicación marcada'), findsOneWidget);
    expect(find.text('Latitud'), findsNothing);
    expect(find.text('Entrega express'), findsOneWidget);
    expect(find.text('COTIZACIÓN DEL ENVÍO'), findsOneWidget);
    expect(find.textContaining('backend'), findsNothing);
    expect(find.textContaining('No hay mapa'), findsNothing);
    expect(find.textContaining('Simular'), findsNothing);
  });

  testWidgets('validates test payment fields without sending card data', (
    tester,
  ) async {
    expect(validateCardNumber('4242 4242 4242 4242'), isNull);
    expect(validateCardNumber('4242'), isNotNull);
    expect(validateCardHolder('  '), isNotNull);
    expect(validateCardExpiry('12/30', now: DateTime(2026, 1)), isNull);
    expect(validateCardExpiry('01/26', now: DateTime(2026, 1)), isNotNull);
    expect(find.text('CVC'), findsNothing);
    expect(find.textContaining('Simular'), findsNothing);
  });

  testWidgets(
    'shows discovered gateway details and disables unavailable methods',
    (tester) async {
      final controller = CartController(api: _FakeCartApi(cart: _deliveryCart));
      await tester.pumpWidget(
        MaterialApp(
          theme: GangaTheme.light(),
          home: CartScreen(
            apiClient: ApiClient(),
            session: null,
            controller: controller,
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.drag(find.byType(ListView), const Offset(0, -500));
      await tester.pumpAndSettle();
      await tester.tap(
        find.widgetWithText(FilledButton, 'Pagar Bs 78,85'),
        warnIfMissed: false,
      );
      await tester.pumpAndSettle();

      expect(find.text('Tarjeta'), findsOneWidget);
      expect(find.textContaining('Pasarela: stripe'), findsOneWidget);
      expect(find.text('QR BCP'), findsOneWidget);
      expect(find.textContaining('No disponible'), findsOneWidget);
      expect(find.text('CVC'), findsNothing);
      expect(find.textContaining('Simular'), findsNothing);
    },
  );

  testWidgets('opens the authenticated PDF action from the paid cart receipt', (
    tester,
  ) async {
    final controller = CartController(api: _FakeCartApi(cart: _deliveryCart));
    controller.receipt = PaymentResult(
      approved: true,
      receiptNumber: 'C-4',
      externalReference: 'pay-4',
      sale: _deliveryCart,
    );
    final receiptService = _FakeReceiptService();
    Uint8List? printedBytes;

    await tester.pumpWidget(
      MaterialApp(
        theme: GangaTheme.light(),
        home: CartScreen(
          apiClient: ApiClient(),
          session: null,
          controller: controller,
          purchaseReceiptService: receiptService,
          purchaseReceiptPdfService: receiptService,
          receiptPdfPrinter: (bytes) async {
            printedBytes = bytes;
            return true;
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Ver comprobante autenticado'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Abrir PDF'));
    await tester.pumpAndSettle();

    expect(receiptService.purchaseId, 5);
    expect(printedBytes, orderedEquals([37, 80, 68, 70]));
  });
}

class _FakeCartApi implements CartDataSource, DeliveryDataSource {
  _FakeCartApi({Cart? cart}) : cart = cart ?? _cart;

  final Cart cart;

  @override
  Future<Cart?> fetchCart() async => cart;

  @override
  Future<List<CartBranch>> fetchBranches() async => const [
    CartBranch(id: 2, name: 'Centro', active: true),
  ];

  @override
  Future<Cart> changeBranch(int branchId) async => cart;

  @override
  Future<Cart> updateQuantity({
    required int lineId,
    required int quantity,
  }) async => cart;

  @override
  Future<Cart> removeLine(int lineId) async => cart;

  @override
  Future<Cart> confirmCart() async => cart;

  @override
  Future<List<PaymentMethod>> fetchPaymentMethods() async => const [
    PaymentMethod(
      value: 'tarjeta',
      label: 'Tarjeta',
      available: true,
      gateway: 'stripe',
      mode: 'simulado',
    ),
    PaymentMethod(
      value: 'qr',
      label: 'QR BCP',
      available: false,
      gateway: 'bcp_qr',
      mode: 'sandbox',
      detail: 'No disponible',
    ),
  ];

  @override
  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required String cardNumber,
  }) async => throw UnimplementedError();

  @override
  Future<QrPayment> createQr({required int saleId}) async =>
      throw UnimplementedError();

  @override
  Future<QrPayment> pollQr({required int saleId, required String qrId}) async =>
      throw UnimplementedError();

  @override
  Future<DeliveryTariff> fetchDeliveryTariff() async =>
      const DeliveryTariff(coverageKilometers: 25);

  @override
  Future<DeliveryQuote> quoteDelivery(DeliveryQuoteInput input) async =>
      DeliveryQuote.fromJson({
        'dentro_de_cobertura': true,
        'desglose': [
          {'concepto': 'Costo de prueba', 'importe': 6.5},
        ],
        'costo_envio': 6.5,
        'distancia_km': 2.5,
        'minutos_estimados': 55,
        'entrega_estimada': '2026-09-21T10:00:00',
        'express': input.express,
        'sucursal': {
          'id': input.branchId,
          'nombre': 'Centro',
          'latitud': 0,
          'longitud': 0,
        },
        'destino': {'latitud': input.latitude, 'longitud': input.longitude},
        'total_a_pagar': 78.85,
      });

  @override
  Future<DeliveryResponse> createDelivery(DeliveryInput input) async =>
      DeliveryResponse(
        sale: cart,
        quote: await quoteDelivery(
          DeliveryQuoteInput(
            branchId: cart.branchId,
            latitude: input.latitude,
            longitude: input.longitude,
            express: input.express,
          ),
        ),
      );

  @override
  Future<Cart> removeDelivery(int shipmentId) async => cart;
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

final _deliveryCart = Cart(
  id: 5,
  status: 'carrito',
  branchId: 2,
  branchName: 'Centro',
  units: 1,
  subtotal: 72.35,
  discount: 17.65,
  total: 78.85,
  receiptNumber: null,
  deliveryType: 'delivery',
  shippingCost: 6.5,
  shipment: const CartShipment(
    id: 15,
    address: 'Av. Siempre Viva 123',
    reference: 'Portón azul',
    latitude: -17.78,
    longitude: -63.18,
    express: false,
  ),
  lines: [
    CartLine(
      id: 9,
      variantId: 10,
      sku: 'GC-10',
      garment: 'Pantalón',
      size: 'L',
      color: 'Negro',
      quantity: 1,
      unitPrice: 90,
      finalPrice: 72.35,
      discount: 17.65,
      promotion: CartPromotion(
        id: 3,
        name: 'Fin de temporada',
        label: '30% OFF',
      ),
      subtotal: 72.35,
      available: 1,
    ),
  ],
);

class _FakeReceiptService
    implements PurchaseReceiptDataSource, PurchaseReceiptPdfDataSource {
  int? purchaseId;

  @override
  Future<PurchaseReceipt> fetchReceipt(int purchaseId) async =>
      const PurchaseReceipt(
        receiptNumber: 'JSON-4',
        dateRaw: null,
        items: [],
        subtotal: 0,
        discount: 0,
        shippingCost: 0,
        delivery: null,
        total: 0,
        currency: 'BOB',
        payment: null,
      );

  @override
  Future<Uint8List> fetchReceiptPdf(int purchaseId) async {
    this.purchaseId = purchaseId;
    return Uint8List.fromList(const [37, 80, 68, 70]);
  }
}
