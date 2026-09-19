import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import 'cart_models.dart';
import 'cart_service.dart';

class CartController extends ChangeNotifier {
  CartController({required this.api});

  final CartDataSource api;

  Cart? cart;
  List<CartBranch> branches = const [];
  PaymentResult? receipt;
  Cart? pendingSale;
  ApiError? error;
  String? feedback;
  bool feedbackIsError = false;
  String? paymentError;
  bool loading = false;
  bool branchChanging = false;
  final Set<int> busyLineIds = <int>{};
  bool paymentProcessing = false;

  bool get hasBusyLines => busyLineIds.isNotEmpty;

  bool isLineBusy(int lineId) => busyLineIds.contains(lineId);

  int? get busyLineId => busyLineIds.firstOrNull;

  bool get canPay =>
      cart != null &&
      cart!.lines.isNotEmpty &&
      !cart!.hasInsufficientStock &&
      !branchChanging &&
      !hasBusyLines &&
      !paymentProcessing;

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      cart = await api.fetchCart();
      try {
        branches = await api.fetchBranches();
      } catch (_) {
        // The cart remains usable when the optional branch list is unavailable.
        branches = const [];
      }
      loading = false;
      notifyListeners();
    } on ApiError catch (caught) {
      loading = false;
      error = caught;
      notifyListeners();
    } catch (caught) {
      loading = false;
      error = _asApiError(caught);
      notifyListeners();
    }
  }

  Future<void> changeBranch(int branchId) async {
    if (branchChanging || paymentProcessing) return;
    branchChanging = true;
    feedback = null;
    notifyListeners();
    try {
      await api.changeBranch(branchId);
      await _refreshCart();
      branchChanging = false;
      notifyListeners();
    } catch (caught) {
      branchChanging = false;
      await _mutationFailure(caught, 'No se pudo cambiar la sucursal.');
    }
  }

  Future<void> updateQuantity(CartLine line, int quantity) async {
    if (isLineBusy(line.id) || paymentProcessing) return;
    if (quantity < 1 || quantity == line.quantity) return;
    if (line.available != null && quantity > line.available!) {
      feedback = 'Solo hay ${line.available} unidades disponibles.';
      feedbackIsError = true;
      notifyListeners();
      return;
    }
    busyLineIds.add(line.id);
    feedback = null;
    notifyListeners();
    try {
      await api.updateQuantity(lineId: line.id, quantity: quantity);
      await _refreshCart();
      busyLineIds.remove(line.id);
      notifyListeners();
    } catch (caught) {
      busyLineIds.remove(line.id);
      await _mutationFailure(caught, 'No se pudo cambiar la cantidad.');
    }
  }

  Future<void> removeLine(CartLine line) async {
    if (isLineBusy(line.id) || paymentProcessing) return;
    busyLineIds.add(line.id);
    feedback = null;
    notifyListeners();
    try {
      await api.removeLine(line.id);
      await _refreshCart();
      busyLineIds.remove(line.id);
      feedback =
          'Quitaste ${line.garment} (${line.size} · ${line.color}) del carrito.';
      feedbackIsError = false;
      notifyListeners();
    } catch (caught) {
      busyLineIds.remove(line.id);
      await _mutationFailure(caught, 'No se pudo quitar la prenda.');
    }
  }

  Future<PaymentResult?> checkout({required bool simulateFailure}) async {
    if (paymentProcessing) return null;
    if (pendingSale == null && !canPay) return null;

    paymentProcessing = true;
    paymentError = null;
    notifyListeners();
    try {
      pendingSale ??= await api.confirmCart();
      final sale = pendingSale!;
      final result = await api.pay(
        saleId: sale.id,
        amount: sale.total,
        simulateFailure: simulateFailure,
      );
      receipt = result;
      pendingSale = null;
      cart = null;
      paymentProcessing = false;
      notifyListeners();
      return result;
    } on ApiError catch (caught) {
      await _paymentFailure(caught);
    } catch (caught) {
      await _paymentFailure(_asApiError(caught));
    }
    return null;
  }

  void clearReceiptAndReload() {
    receipt = null;
    load();
  }

  Future<void> _paymentFailure(ApiError caught) async {
    paymentProcessing = false;
    if (caught.statusCode == 402) {
      pendingSale = null;
      paymentError =
          '${_paymentReason(caught)} Tu carrito sigue intacto: puedes intentar de nuevo.';
      notifyListeners();
      await _refreshCart();
      return;
    }
    if (pendingSale != null) {
      paymentError =
          '${caught.message} Tu compra quedó confirmada y pendiente de pago: puedes reintentar.';
      notifyListeners();
      return;
    }
    paymentError = 'No se pudo confirmar el carrito: ${caught.message}';
    notifyListeners();
    await _refreshCart();
  }

  Future<void> _refreshCart() async {
    try {
      cart = await api.fetchCart();
      error = null;
      notifyListeners();
    } on ApiError catch (caught) {
      error = caught;
      notifyListeners();
    } catch (caught) {
      error = _asApiError(caught);
      notifyListeners();
    }
  }

  Future<void> _mutationFailure(Object caught, String fallback) async {
    final normalized = _asApiError(caught, fallback: fallback);
    feedback = normalized.message;
    feedbackIsError = true;
    notifyListeners();
    await load();
  }

  static String _paymentReason(ApiError error) {
    final details = error.details;
    if (details is Map && details['motivo'] is String) {
      final reason = (details['motivo'] as String).trim();
      if (reason.isNotEmpty) return reason.endsWith('.') ? reason : '$reason.';
    }
    return 'La pasarela rechazó el pago.';
  }

  static ApiError _asApiError(Object caught, {String? fallback}) {
    if (caught is ApiError) return caught;
    return ApiError(statusCode: 0, message: '$fallback $caught'.trim());
  }
}
