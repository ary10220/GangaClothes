import '../../core/network/api_client.dart';
import 'purchase_history_models.dart';

abstract interface class PurchaseHistoryDataSource {
  Future<List<Purchase>> fetchPurchases();
}

abstract interface class PurchaseReceiptDataSource {
  Future<PurchaseReceipt> fetchReceipt(int purchaseId);
}

class PurchaseHistoryService
    implements PurchaseHistoryDataSource, PurchaseReceiptDataSource {
  const PurchaseHistoryService(this.apiClient);

  static const bool supportsPdfReceiptAction = false;
  static const pdfCapabilityGap =
      'ApiClient can receive authenticated PDF bytes with Dio options, but '
      'the app has no existing PDF viewer, file storage, or file-opening '
      'capability; the PDF endpoint remains outside the UI.';

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

  @override
  Future<PurchaseReceipt> fetchReceipt(int purchaseId) async {
    final response = await apiClient.request<Object?>(
      '/ventas/$purchaseId/comprobante',
    );
    if (response.data is! Map) {
      throw const FormatException('Purchase receipt response is not an object');
    }
    return PurchaseReceipt.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }
}
