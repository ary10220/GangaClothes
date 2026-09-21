import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/cart/cart_controller.dart';
import 'package:mobile/features/cart/cart_models.dart';
import 'package:mobile/features/cart/cart_service.dart';
import 'package:mobile/features/delivery/delivery_models.dart';
import 'package:mobile/features/delivery/delivery_service.dart';

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

    expect(await controller.checkout(cardNumber: '4242424242424242'), isNull);
    expect(api.confirmCalls, 1);
    expect(controller.pendingSale, isNotNull);
    expect(controller.paymentError, contains('pendiente'));

    api.paymentError = null;
    final receipt = await controller.checkout(cardNumber: '4242424242424242');
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

    await controller.checkout(cardNumber: '4000000000000002');

    expect(controller.pendingSale, isNull);
    expect(controller.paymentError, contains('Card declined (simulado).'));
    expect(api.fetchCartCalls, greaterThan(1));
  });

  test(
    'keeps delivery totals and payment eligibility from the cart response',
    () async {
      final controller = CartController(
        api: _FakeCartApi(
          cart: _cart(
            deliveryType: 'delivery',
            shippingCost: 6.5,
            shipment: const CartShipment(
              id: 12,
              address: 'Calle 10 #45',
              latitude: -17.78,
              longitude: -63.18,
              express: false,
            ),
          ),
        ),
      );

      await controller.load();

      expect(controller.cart?.deliveryType, 'delivery');
      expect(controller.cart?.shippingCost, 6.5);
      expect(controller.cart?.shipment?.address, 'Calle 10 #45');
      expect(controller.cart?.branchName, 'Centro');
      expect(controller.canPay, isTrue);
    },
  );

  test('keeps only available discovered methods selectable', () async {
    final controller = CartController(api: _FakeCartApi());

    await controller.loadPaymentMethods();

    expect(controller.paymentMethods, hasLength(2));
    expect(controller.availablePaymentMethods.map((method) => method.value), [
      'tarjeta',
    ]);
  });

  test('approves a QR and protects against duplicate submits', () async {
    final api = _FakeCartApi(
      cart: _cart(),
      qrPollResults: [_qr(state: QrPaymentState.approved, withResult: true)],
    );
    final controller = CartController(api: api);
    await controller.load();

    await Future.wait([
      controller.startQrPayment(),
      controller.startQrPayment(),
    ]);
    await Future<void>.delayed(Duration.zero);

    expect(api.confirmCalls, 1);
    expect(api.createQrCalls, 1);
    expect(api.pollQrCalls, 1);
    expect(controller.receipt?.paymentLabel, 'QR (BCP)');
    controller.dispose();
  });

  test('cancels QR polling on disposal', () async {
    final api = _FakeCartApi(
      cart: _cart(),
      qrPollResults: [_qr(state: QrPaymentState.pending)],
    );
    final controller = CartController(api: api);
    await controller.load();

    await controller.startQrPayment();
    final callsBeforeDispose = api.pollQrCalls;
    controller.dispose();
    await Future<void>.delayed(const Duration(milliseconds: 10));

    expect(api.pollQrCalls, callsBeforeDispose);
  });

  test(
    'returns expired and annulled QR payments to a retryable cart',
    () async {
      for (final terminalState in [
        QrPaymentState.expired,
        QrPaymentState.annulled,
      ]) {
        final api = _FakeCartApi(
          cart: _cart(),
          qrPollResults: [_qr(state: terminalState)],
        );
        final controller = CartController(api: api);
        await controller.load();
        await controller.startQrPayment();
        await Future<void>.delayed(Duration.zero);

        expect(controller.pendingSale, isNull);
        expect(controller.paymentError, isNotNull);
        expect(controller.cart, isNotNull);
        controller.dispose();
      }
    },
  );
}

class _FakeCartApi implements CartDataSource, DeliveryDataSource {
  _FakeCartApi({this.cart, this.paymentError, List<QrPayment>? qrPollResults})
    : qrPollResults = [...?qrPollResults];

  Cart? cart;
  ApiError? paymentError;
  int fetchCartCalls = 0;
  int confirmCalls = 0;
  int paymentCalls = 0;
  int createQrCalls = 0;
  int pollQrCalls = 0;
  final List<QrPayment> qrPollResults;

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
      label: 'QR',
      available: false,
      gateway: 'bcp_qr',
      mode: 'simulado',
    ),
  ];

  @override
  Future<QrPayment> createQr({required int saleId}) async {
    createQrCalls++;
    return _qr(state: QrPaymentState.pending);
  }

  @override
  Future<QrPayment> pollQr({required int saleId, required String qrId}) async {
    pollQrCalls++;
    return qrPollResults.isEmpty
        ? _qr(state: QrPaymentState.pending)
        : qrPollResults.removeAt(0);
  }

  @override
  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required String cardNumber,
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
        'total_a_pagar': 86.5,
      });

  @override
  Future<DeliveryResponse> createDelivery(DeliveryInput input) async =>
      DeliveryResponse(
        sale: cart!,
        quote: await quoteDelivery(
          DeliveryQuoteInput(
            branchId: cart!.branchId,
            latitude: input.latitude,
            longitude: input.longitude,
            express: input.express,
          ),
        ),
      );

  @override
  Future<Cart> removeDelivery(int shipmentId) async => cart!;
}

QrPayment _qr({required QrPaymentState state, bool withResult = false}) =>
    QrPayment(
      saleId: 4,
      qrId: 'qr-4',
      state: state,
      paymentResult: withResult
          ? PaymentResult(
              approved: true,
              sale: _cart(status: 'pagada'),
              receiptNumber: 'C-000002',
              externalReference: 'qr-4',
              paymentLabel: 'QR (BCP)',
            )
          : null,
    );

Cart _cart({
  bool reaches = true,
  String status = 'carrito',
  String deliveryType = 'sucursal',
  double? shippingCost,
  CartShipment? shipment,
}) => Cart(
  id: 4,
  status: status,
  branchId: 2,
  branchName: 'Centro',
  units: 1,
  subtotal: 80,
  discount: 0,
  total: 80,
  receiptNumber: null,
  deliveryType: deliveryType,
  shippingCost: shippingCost,
  shipment: shipment,
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
