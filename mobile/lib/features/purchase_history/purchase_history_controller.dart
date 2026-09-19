import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import 'purchase_history_models.dart';
import 'purchase_history_service.dart';

class PurchaseHistoryController extends ChangeNotifier {
  PurchaseHistoryController({required this.api});

  final PurchaseHistoryDataSource api;

  List<Purchase> purchases = const [];
  ApiError? error;
  bool loading = false;

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
