import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../core/network/api_client.dart';
import 'purchase_history_models.dart';

abstract interface class PurchaseHistoryDataSource {
  Future<List<Purchase>> fetchPurchases();
}

abstract interface class PurchaseReceiptDataSource {
  Future<PurchaseReceipt> fetchReceipt(int purchaseId);
}

abstract interface class PurchaseReceiptPdfDataSource {
  Future<Uint8List> fetchReceiptPdf(int purchaseId);
}

class PurchaseHistoryService
    implements
        PurchaseHistoryDataSource,
        PurchaseReceiptDataSource,
        PurchaseReceiptPdfDataSource {
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

  @override
  Future<Uint8List> fetchReceiptPdf(int purchaseId) async {
    final response = await apiClient.request<Object?>(
      '/ventas/$purchaseId/comprobante.pdf',
      options: Options(responseType: ResponseType.bytes),
    );
    final data = response.data;
    if (data is Uint8List) return data;
    if (data is List<int>) return Uint8List.fromList(data);
    throw const FormatException('Purchase receipt PDF response is not bytes');
  }
}
