import '../../core/network/api_client.dart';
import '../../core/network/api_error.dart';
import 'catalog_detail_models.dart';

abstract interface class CatalogActionDataSource {
  Future<ReservationSummary> createReservation(ReservationRequest request);

  Future<CartSummary?> fetchCart();

  Future<CartSummary> openCart({required int branchId});

  Future<CartSummary> addCartItem({
    required int variantId,
    required int quantity,
  });
}

class CatalogActionService implements CatalogActionDataSource {
  const CatalogActionService(this.apiClient);

  final ApiClient apiClient;

  @override
  Future<ReservationSummary> createReservation(
    ReservationRequest request,
  ) async {
    final response = await apiClient.request<Object?>(
      '/reservas',
      method: 'POST',
      data: request.toJson(),
    );
    return ReservationSummary.fromJson(_map(response.data));
  }

  @override
  Future<CartSummary?> fetchCart() async {
    try {
      final response = await apiClient.request<Object?>('/ventas/carrito');
      return CartSummary.fromJson(_map(response.data));
    } on ApiError catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<CartSummary> openCart({required int branchId}) async {
    final response = await apiClient.request<Object?>(
      '/ventas/carrito',
      method: 'POST',
      data: {'sucursal_id': branchId, 'canal': 'movil'},
    );
    return CartSummary.fromJson(_map(response.data));
  }

  @override
  Future<CartSummary> addCartItem({
    required int variantId,
    required int quantity,
  }) async {
    final response = await apiClient.request<Object?>(
      '/ventas/carrito/items',
      method: 'POST',
      data: {'variante_id': variantId, 'cantidad': quantity},
    );
    return CartSummary.fromJson(_map(response.data));
  }
}

Map<String, dynamic> _map(Object? value) {
  if (value is! Map) throw const FormatException('Expected a JSON object');
  return Map<String, dynamic>.from(value);
}
