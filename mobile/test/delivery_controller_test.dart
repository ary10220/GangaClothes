import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/cart/cart_controller.dart';
import 'package:mobile/features/cart/cart_models.dart';
import 'package:mobile/features/cart/cart_service.dart';
import 'package:mobile/features/delivery/delivery_models.dart';
import 'package:mobile/features/delivery/delivery_service.dart';

void main() {
  test(
    'moves between pickup and delivery and preserves backend payment total',
    () async {
      final api = _FakeDeliveryCartApi(cart: _cart());
      final controller = CartController(api: api);
      await controller.load();

      expect(controller.canPay, isTrue);
      controller.beginDeliveryEditing();
      const input = DeliveryInput(
        saleId: 4,
        address: 'Calle 10 #45',
        reference: 'Portón azul',
        contactPhone: '70000000',
        latitude: -17.78,
        longitude: -63.18,
        express: true,
      );
      const quoteInput = DeliveryQuoteInput(
        branchId: 2,
        latitude: -17.78,
        longitude: -63.18,
        express: true,
      );
      await controller.quoteDelivery(quoteInput);
      expect(controller.canPay, isFalse);
      expect(api.lastQuoteInput?.express, isTrue);

      expect(await controller.createDelivery(input), isTrue);
      expect(controller.cart?.deliveryType, 'delivery');
      expect(controller.cart?.total, 92.5);
      expect(api.lastCreateInput?.toJson(), input.toJson());
      controller.endDeliveryEditing();
      expect(controller.canPay, isTrue);

      await controller.checkout(cardNumber: '4242424242424242');
      expect(api.lastPaymentAmount, 92.5);

      final afterPickup = await controller.removeDelivery();
      expect(afterPickup, isFalse);
      // A paid sale cannot switch back to pickup; the controller keeps the
      // payment flow authoritative rather than inventing a local cart change.
    },
  );

  test(
    'uses the DELETE response for a pickup transition before payment',
    () async {
      final api = _FakeDeliveryCartApi(cart: _deliveryCart());
      final controller = CartController(api: api);
      await controller.load();
      expect(controller.canPay, isTrue);

      controller.beginDeliveryEditing();
      expect(await controller.removeDelivery(), isTrue);
      expect(api.lastRemovedShipmentId, 9);
      expect(controller.cart?.deliveryType, 'sucursal');
      expect(controller.cart?.shippingCost, 0);
      expect(controller.deliveryQuote, isNull);
      controller.endDeliveryEditing();
      expect(controller.canPay, isTrue);
    },
  );

  test('blocks payment for an outside-coverage saved delivery', () async {
    final api = _FakeDeliveryCartApi(cart: _deliveryCart(), outside: true);
    final controller = CartController(api: api);
    await controller.load();

    expect(controller.deliveryQuote?.withinCoverage, isFalse);
    expect(controller.canPay, isFalse);
    expect(controller.deliveryQuoteReady, isFalse);
  });

  test('keeps delivery creation retryable after a transient failure', () async {
    final api = _FakeDeliveryCartApi(
      cart: _cart(),
      createError: const ApiError(statusCode: 503, message: 'Servidor ocupado'),
    );
    final controller = CartController(api: api);
    await controller.load();
    controller.beginDeliveryEditing();
    const input = DeliveryInput(
      saleId: 4,
      address: 'Calle 10 #45',
      contactPhone: '70000000',
      latitude: -17.78,
      longitude: -63.18,
      express: false,
    );
    await controller.quoteDelivery(
      const DeliveryQuoteInput(
        branchId: 2,
        latitude: -17.78,
        longitude: -63.18,
        express: false,
      ),
    );

    expect(await controller.createDelivery(input), isFalse);
    expect(controller.cart?.deliveryType, 'sucursal');
    expect(controller.deliveryError?.statusCode, 503);
    api.createError = null;
    expect(await controller.createDelivery(input), isTrue);
    expect(controller.cart?.total, 92.5);
  });
}

class _FakeDeliveryCartApi implements CartDataSource, DeliveryDataSource {
  _FakeDeliveryCartApi({
    required this.cart,
    this.outside = false,
    this.createError,
  });

  Cart cart;
  final bool outside;
  ApiError? createError;
  DeliveryQuoteInput? lastQuoteInput;
  DeliveryInput? lastCreateInput;
  int? lastRemovedShipmentId;
  double? lastPaymentAmount;

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
  Future<List<PaymentMethod>> fetchPaymentMethods() async => const [];

  @override
  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required String cardNumber,
  }) async {
    lastPaymentAmount = amount;
    return PaymentResult(approved: true, sale: cart, receiptNumber: 'C-1');
  }

  @override
  Future<QrPayment> createQr({required int saleId}) =>
      throw UnimplementedError();

  @override
  Future<QrPayment> pollQr({required int saleId, required String qrId}) =>
      throw UnimplementedError();

  @override
  Future<DeliveryTariff> fetchDeliveryTariff() async =>
      const DeliveryTariff(coverageKilometers: 25);

  @override
  Future<DeliveryQuote> quoteDelivery(DeliveryQuoteInput input) async {
    lastQuoteInput = input;
    return DeliveryQuote.fromJson({
      'dentro_de_cobertura': !outside,
      'mensaje_cobertura': outside ? 'Fuera de cobertura' : null,
      'desglose': [
        {'concepto': 'Envío', 'importe': outside ? 0 : 12.5},
      ],
      'costo_envio': outside ? 0 : 12.5,
      'distancia_km': outside ? 40 : 4,
      'minutos_estimados': 60,
      'entrega_estimada': '2026-09-21T10:00:00',
      'express': input.express,
      'sucursal': {
        'id': input.branchId,
        'nombre': 'Centro',
        'latitud': 0,
        'longitud': 0,
      },
      'destino': {'latitud': input.latitude, 'longitud': input.longitude},
      'total_a_pagar': outside ? 80 : 92.5,
    });
  }

  @override
  Future<DeliveryResponse> createDelivery(DeliveryInput input) async {
    lastCreateInput = input;
    if (createError != null) throw createError!;
    cart = _deliveryCart(total: 92.5, express: input.express);
    return DeliveryResponse(
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
  }

  @override
  Future<Cart> removeDelivery(int shipmentId) async {
    lastRemovedShipmentId = shipmentId;
    cart = _cart();
    return cart;
  }
}

Cart _cart() => Cart(
  id: 4,
  status: 'carrito',
  branchId: 2,
  branchName: 'Centro',
  units: 1,
  subtotal: 80,
  discount: 0,
  total: 80,
  receiptNumber: null,
  shippingCost: 0,
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
    ),
  ],
);

Cart _deliveryCart({double total = 92.5, bool express = false}) => Cart(
  id: 4,
  status: 'carrito',
  branchId: 2,
  branchName: 'Centro',
  units: 1,
  subtotal: 80,
  discount: 0,
  total: total,
  receiptNumber: null,
  deliveryType: 'delivery',
  shippingCost: total - 80,
  shipment: CartShipment(
    id: 9,
    address: 'Calle 10 #45',
    contactPhone: '70000000',
    latitude: -17.78,
    longitude: -63.18,
    express: express,
  ),
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
    ),
  ],
);
