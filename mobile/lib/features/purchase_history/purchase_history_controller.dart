import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import 'purchase_history_models.dart';
import 'purchase_history_service.dart';

class PurchaseHistoryController extends ChangeNotifier {
  PurchaseHistoryController({required this.api, this.receiptApi});

  final PurchaseHistoryDataSource api;
  final PurchaseReceiptDataSource? receiptApi;

  List<Purchase> purchases = const [];
  ApiError? error;
  bool loading = false;
  PurchaseReceipt? receipt;
  ApiError? receiptError;
  int? receiptPurchaseId;
  bool receiptLoading = false;

  Future<void> load() async {
    loading = true;
    error = null;
    _notify();
    try {
      purchases = await api.fetchPurchases();
      loading = false;
      _notify();
    } catch (caught) {
      loading = false;
      error = _asApiError(caught);
      _notify();
    }
  }

  Future<PurchaseReceipt?> loadReceipt(int purchaseId) async {
    final source = receiptApi;
    if (source == null) return null;

    receiptLoading = true;
    receiptError = null;
    receiptPurchaseId = purchaseId;
    _notify();
    try {
      receipt = await source.fetchReceipt(purchaseId);
      receiptLoading = false;
      _notify();
      return receipt;
    } catch (caught) {
      receiptLoading = false;
      receipt = null;
      receiptError = _asReceiptApiError(caught);
      _notify();
      return null;
    }
  }

  void _notify() {
    if (hasListeners) notifyListeners();
  }
}

ApiError _asApiError(Object error) {
  if (error is ApiError) return error;
  return ApiError(
    statusCode: 0,
    message: 'No se pudieron cargar tus compras.',
    cause: error,
  );
}

ApiError _asReceiptApiError(Object error) {
  if (error is ApiError) return error;
  return ApiError(
    statusCode: 0,
    message: 'No se pudo cargar el comprobante.',
    cause: error,
  );
}
