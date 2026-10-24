import '../../core/network/api_client.dart';
import '../cart/cart_models.dart';
import 'delivery_models.dart';

abstract interface class DeliveryDataSource {
  Future<DeliveryTariff> fetchDeliveryTariff();

  Future<DeliveryQuote> quoteDelivery(DeliveryQuoteInput input);

  Future<DeliveryResponse> createDelivery(DeliveryInput input);

  Future<Cart> removeDelivery(int shipmentId);
}

class DeliveryService implements DeliveryDataSource {
  const DeliveryService(this.apiClient);

  final ApiClient apiClient;

  @override
  Future<DeliveryTariff> fetchDeliveryTariff() async {
    final response = await apiClient.request<Object?>('/envios/tarifa');
    return DeliveryTariff.fromJson(_map(response.data));
  }

  @override
  Future<DeliveryQuote> quoteDelivery(DeliveryQuoteInput input) async {
    final response = await apiClient.request<Object?>(
      '/envios/cotizar',
      method: 'POST',
      data: input.toJson(),
    );
    return DeliveryQuote.fromJson(_map(response.data));
  }

  @override
  Future<DeliveryResponse> createDelivery(DeliveryInput input) async {
    final response = await apiClient.request<Object?>(
      '/envios',
      method: 'POST',
      data: input.toJson(),
    );
    return DeliveryResponse.fromJson(_map(response.data));
  }

  @override
  Future<Cart> removeDelivery(int shipmentId) async {
    final response = await apiClient.request<Object?>(
      '/envios/$shipmentId',
      method: 'DELETE',
    );
    return Cart.fromJson(_map(response.data));
  }
}

Map<String, dynamic> _map(Object? value) {
  if (value is! Map) throw const FormatException('Expected a JSON object');
  return Map<String, dynamic>.from(value);
}
