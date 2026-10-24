import '../../core/network/api_client.dart';
import '../../core/network/api_error.dart';
import '../delivery/delivery_models.dart';
import '../delivery/delivery_service.dart';
import 'cart_models.dart';

abstract interface class CartDataSource {
  Future<Cart?> fetchCart();

  Future<List<CartBranch>> fetchBranches();

  Future<Cart> changeBranch(int branchId);

  Future<Cart> updateQuantity({required int lineId, required int quantity});

  Future<Cart> removeLine(int lineId);

  Future<Cart> confirmCart();

  Future<List<PaymentMethod>> fetchPaymentMethods();

  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required String cardNumber,
  });

  Future<QrPayment> createQr({required int saleId});

  Future<QrPayment> pollQr({required int saleId, required String qrId});
}

class CartService implements CartDataSource, DeliveryDataSource {
  const CartService(this.apiClient);

  final ApiClient apiClient;

  DeliveryService get _deliveryService => DeliveryService(apiClient);

  @override
  Future<Cart?> fetchCart() async {
    try {
      final response = await apiClient.request<Object?>('/ventas/carrito');
      return Cart.fromJson(_map(response.data));
    } on ApiError catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<List<CartBranch>> fetchBranches() async {
    final response = await apiClient.request<Object?>('/admin/sucursales');
    final data = response.data;
    if (data is! List) {
      throw const FormatException('Branch response is not a list');
    }
    return data
        .whereType<Map>()
        .map((item) => CartBranch.fromJson(Map<String, dynamic>.from(item)))
        .where((branch) => branch.active)
        .toList(growable: false);
  }

  @override
  Future<Cart> changeBranch(int branchId) => _cartRequest(
    '/ventas/carrito',
    method: 'POST',
    data: {'sucursal_id': branchId},
  );

  @override
  Future<Cart> updateQuantity({required int lineId, required int quantity}) =>
      _cartRequest(
        '/ventas/carrito/items/$lineId',
        method: 'PUT',
        data: {'cantidad': quantity},
      );

  @override
  Future<Cart> removeLine(int lineId) =>
      _cartRequest('/ventas/carrito/items/$lineId', method: 'DELETE');

  @override
  Future<Cart> confirmCart() => _cartRequest(
    '/ventas/carrito/confirmar',
    method: 'POST',
    data: const <String, dynamic>{},
  );

  @override
  Future<List<PaymentMethod>> fetchPaymentMethods() async {
    final response = await apiClient.request<Object?>(
      '/pagos/metodos',
      queryParameters: const {'canal': 'movil'},
    );
    final data = _map(response.data)['metodos'];
    if (data is! List) {
      throw const FormatException('Payment method response is not a list');
    }
    return data
        .whereType<Map>()
        .map((item) => PaymentMethod.fromJson(Map<String, dynamic>.from(item)))
        .toList(growable: false);
  }

  @override
  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required String cardNumber,
  }) async {
    final response = await apiClient.request<Object?>(
      '/pagos',
      method: 'POST',
      data: {
        'venta_id': saleId,
        'metodo': 'tarjeta',
        'monto': amount,
        'numero_tarjeta': cardNumber,
      },
    );
    return PaymentResult.fromJson(_map(response.data));
  }

  @override
  Future<QrPayment> createQr({required int saleId}) async {
    final response = await apiClient.request<Object?>(
      '/pagos/qr',
      method: 'POST',
      data: {'venta_id': saleId},
    );
    return QrPayment.fromJson(_map(response.data));
  }

  @override
  Future<QrPayment> pollQr({required int saleId, required String qrId}) async {
    final response = await apiClient.request<Object?>(
      '/pagos/qr/$qrId',
      queryParameters: {'venta_id': saleId},
    );
    return QrPayment.fromJson(_map(response.data));
  }

  @override
  Future<DeliveryTariff> fetchDeliveryTariff() =>
      _deliveryService.fetchDeliveryTariff();

  @override
  Future<DeliveryQuote> quoteDelivery(DeliveryQuoteInput input) =>
      _deliveryService.quoteDelivery(input);

  @override
  Future<DeliveryResponse> createDelivery(DeliveryInput input) =>
      _deliveryService.createDelivery(input);

  @override
  Future<Cart> removeDelivery(int shipmentId) =>
      _deliveryService.removeDelivery(shipmentId);

  Future<Cart> _cartRequest(
    String path, {
    required String method,
    Object? data,
  }) async {
    final response = await apiClient.request<Object?>(
      path,
      method: method,
      data: data,
    );
    return Cart.fromJson(_map(response.data));
  }
}

Map<String, dynamic> _map(Object? value) {
  if (value is! Map) throw const FormatException('Expected a JSON object');
  return Map<String, dynamic>.from(value);
}
