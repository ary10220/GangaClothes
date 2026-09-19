import '../../core/network/api_client.dart';
import 'purchase_history_models.dart';

abstract interface class PurchaseHistoryDataSource {
  Future<List<Purchase>> fetchPurchases();
}

class PurchaseHistoryService implements PurchaseHistoryDataSource {
  const PurchaseHistoryService(this.apiClient);

  final ApiClient apiClient;

  @override
  Future<List<Purchase>> fetchPurchases() async {
    final response = await apiClient.request<Object?>('/ventas/mias');
    if (response.data is! List) {
      throw const FormatException('Purchase history response is not a list');
    }
    return (response.data as List)
        .whereType<Map>()
        .map((item) => Purchase.fromJson(Map<String, dynamic>.from(item)))
        .toList(growable: false);
  }
}
