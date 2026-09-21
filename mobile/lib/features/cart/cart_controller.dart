import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import 'cart_models.dart';
import 'cart_service.dart';

class CartController extends ChangeNotifier {
  CartController({required this.api});

  final CartDataSource api;

  Cart? cart;
  List<CartBranch> branches = const [];
  List<PaymentMethod> paymentMethods = const [];
  PaymentResult? receipt;
  Cart? pendingSale;
  QrPayment? qrPayment;
  ApiError? error;
  ApiError? paymentMethodsError;
  String? feedback;
  bool feedbackIsError = false;
  String? paymentError;
  bool loading = false;
  bool branchChanging = false;
  bool paymentMethodsLoading = false;
  bool qrPolling = false;
  final Set<int> busyLineIds = <int>{};
  bool paymentProcessing = false;
  Timer? _qrTimer;
  bool _qrRequestInFlight = false;
  bool _disposed = false;

  bool get hasBusyLines => busyLineIds.isNotEmpty;

  bool isLineBusy(int lineId) => busyLineIds.contains(lineId);

  int? get busyLineId => busyLineIds.firstOrNull;

  List<PaymentMethod> get availablePaymentMethods => paymentMethods
      .where((method) => method.available && method.value.isNotEmpty)
      .toList(growable: false);

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
      await loadPaymentMethods();
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

  Future<void> loadPaymentMethods() async {
    paymentMethodsLoading = true;
    paymentMethodsError = null;
    notifyListeners();
    try {
      paymentMethods = await api.fetchPaymentMethods();
    } on ApiError catch (caught) {
      paymentMethodsError = caught;
      paymentMethods = const [];
    } catch (caught) {
      paymentMethodsError = _asApiError(caught);
      paymentMethods = const [];
    } finally {
      paymentMethodsLoading = false;
      if (!_disposed) notifyListeners();
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

  Future<PaymentResult?> checkout({required String cardNumber}) async {
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
        cardNumber: cardNumber,
      );
      receipt = result;
      pendingSale = null;
      cart = null;
      qrPayment = null;
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

  Future<void> startQrPayment() async {
    if (paymentProcessing || _disposed) return;
    if (pendingSale == null && !canPay) return;
    if (qrPayment?.isPending == true && pendingSale != null) {
      _startQrPolling();
      return;
    }

    paymentProcessing = true;
    paymentError = null;
    notifyListeners();
    try {
      pendingSale ??= await api.confirmCart();
      final sale = pendingSale!;
      final qr = await api.createQr(saleId: sale.id);
      if (_disposed) return;
      qrPayment = qr;
      paymentProcessing = false;
      notifyListeners();
      if (qr.isPending) _startQrPolling();
    } on ApiError catch (caught) {
      await _qrFailure(caught);
    } catch (caught) {
      await _qrFailure(_asApiError(caught));
    }
  }

  Future<void> pollQr() async {
    if (_disposed || _qrRequestInFlight || pendingSale == null) return;
    final qr = qrPayment;
    if (qr == null || !qr.isPending) {
      _stopQrPolling();
      return;
    }

    _qrRequestInFlight = true;
    try {
      final updated = await api.pollQr(saleId: pendingSale!.id, qrId: qr.qrId);
      if (_disposed) return;
      qrPayment = updated;
      if (updated.state == QrPaymentState.approved &&
          updated.paymentResult != null) {
        _stopQrPolling();
        receipt = updated.paymentResult;
        pendingSale = null;
        cart = null;
        paymentProcessing = false;
        notifyListeners();
      } else if (updated.isTerminal) {
        await _qrTerminal(updated);
      } else {
        notifyListeners();
      }
    } on ApiError catch (caught) {
      if (_disposed) return;
      if (caught.statusCode == 402) {
        final details = caught.details;
        if (details is Map) {
          final terminal = QrPayment.fromJson(
            Map<String, dynamic>.from(details),
          );
          if (terminal.qrId.isNotEmpty && terminal.qrId == qr.qrId) {
            qrPayment = terminal;
            await _qrTerminal(terminal);
            return;
          }
        }
        await _paymentFailure(caught);
      } else if (caught.statusCode >= 500 || caught.statusCode == 0) {
        // A transient gateway failure must not lose the confirmed sale or stop
        // asking the bank about the same QR.
        paymentError = '${caught.message} Reintentando la consulta…';
        notifyListeners();
      } else {
        _stopQrPolling();
        paymentProcessing = false;
        paymentError = caught.message;
        notifyListeners();
      }
    } catch (caught) {
      if (!_disposed) {
        paymentError = '$caught Reintentando la consulta…';
        notifyListeners();
      }
    } finally {
      _qrRequestInFlight = false;
    }
  }

  void _startQrPolling() {
    if (_disposed || qrPayment?.isPending != true || qrPolling) return;
    qrPolling = true;
    _qrTimer = Timer.periodic(
      const Duration(seconds: 3),
      (_) => unawaited(pollQr()),
    );
    unawaited(pollQr());
    notifyListeners();
  }

  void _stopQrPolling() {
    _qrTimer?.cancel();
    _qrTimer = null;
    qrPolling = false;
  }

  Future<void> _qrTerminal(QrPayment qr) async {
    _stopQrPolling();
    paymentProcessing = false;
    pendingSale = null;
    paymentError = switch (qr.state) {
      QrPaymentState.expired =>
        'El QR venció antes de que se pagara. Tu carrito sigue intacto: puedes intentar de nuevo.',
      QrPaymentState.annulled =>
        'El QR fue anulado. Tu carrito sigue intacto: puedes intentar de nuevo.',
      _ => null,
    };
    notifyListeners();
    await _refreshCart();
  }

  Future<void> _qrFailure(ApiError caught) async {
    paymentProcessing = false;
    if (caught.statusCode == 402) {
      await _paymentFailure(caught);
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

  void clearReceiptAndReload() {
    receipt = null;
    load();
  }

  Future<void> _paymentFailure(ApiError caught) async {
    _stopQrPolling();
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

  @override
  void dispose() {
    _disposed = true;
    _stopQrPolling();
    super.dispose();
  }
}
