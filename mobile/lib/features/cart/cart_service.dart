import '../../core/network/api_client.dart';
import '../../core/network/api_error.dart';
import 'cart_models.dart';

abstract interface class CartDataSource {
  Future<Cart?> fetchCart();

  Future<List<CartBranch>> fetchBranches();

  Future<Cart> changeBranch(int branchId);

  Future<Cart> updateQuantity({required int lineId, required int quantity});

  Future<Cart> removeLine(int lineId);

  Future<Cart> confirmCart();

  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required bool simulateFailure,
  });
}

class CartService implements CartDataSource {
  const CartService(this.apiClient);

  final ApiClient apiClient;

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
  Future<PaymentResult> pay({
    required int saleId,
    required double amount,
    required bool simulateFailure,
  }) async {
    final response = await apiClient.request<Object?>(
      '/pagos',
      method: 'POST',
      data: {
        'venta_id': saleId,
        'metodo': 'pasarela',
        'monto': amount,
        'simular_fallo': simulateFailure,
      },
    );
    return PaymentResult.fromJson(_map(response.data));
  }

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
