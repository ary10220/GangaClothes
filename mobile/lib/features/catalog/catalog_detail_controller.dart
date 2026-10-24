import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import 'catalog_detail_models.dart';
import 'catalog_detail_service.dart';
import 'catalog_models.dart';
import '../ai/ai_service.dart';

enum CatalogDetailMode { choose, reserve }

class CartBranchConflict {
  const CartBranchConflict({required this.from, required this.to});

  final String from;
  final String to;
}

class CatalogDetailController extends ChangeNotifier {
  CatalogDetailController({
    required this.product,
    required this.branches,
    required this.api,
    this.preferredBranchId,
    this.aiEventSink,
  }) {
    _initializeSelection();
  }

  final Product product;
  final List<BranchOption> branches;
  final CatalogActionDataSource api;
  final int? preferredBranchId;
  final AiEventSink? aiEventSink;

  late int? colorId;
  late int? sizeId;
  int? branchId;
  int quantity = 1;
  CatalogDetailMode mode = CatalogDetailMode.choose;
  DateTime? visitAt;
  String notes = '';
  bool loading = false;
  String? error;
  String? success;
  String? successRoute;
  CartBranchConflict? cartConflict;

  List<CatalogColorChoice> get colors => colorChoices(product);

  List<CatalogSizeChoice> get sizes => sizeChoices(product);

  Variant? get selectedVariant {
    for (final variant in product.variants) {
      if (variant.colorId == colorId && variant.sizeId == sizeId) {
        return variant;
      }
    }
    return null;
  }

  List<Availability> get availability => selectedVariant?.availability ?? [];

  List<Availability> get branchesWithStock =>
      availability.where((row) => row.available > 0).toList(growable: false);

  String? get selectedBranchName => availability
      .where((row) => row.branchId == branchId)
      .map((row) => row.branchName)
      .firstOrNull;

  int get selectedBranchAvailability =>
      availability
          .where((row) => row.branchId == branchId)
          .map((row) => row.available)
          .firstOrNull ??
      0;

  String? get actionBlockReason {
    final variant = selectedVariant;
    if (variant == null) return 'Elige una talla y un color.';
    if (variant.availableTotal <= 0 || branchesWithStock.isEmpty) {
      return 'Esta talla y color estan agotados.';
    }
    if (branchId == null) return 'Elige la sucursal.';
    if (quantity < 1) return 'La cantidad minima es 1.';
    if (quantity > selectedBranchAvailability) {
      return 'Solo hay $selectedBranchAvailability disponibles en '
          '${selectedBranchName ?? 'la sucursal elegida'}.';
    }
    return null;
  }

  bool sizeUnavailable(int candidateSizeId) {
    final variant = product.variants
        .where(
          (item) => item.colorId == colorId && item.sizeId == candidateSizeId,
        )
        .firstOrNull;
    return variant == null || variant.availableTotal <= 0;
  }

  void selectColor(int value) {
    if (mode == CatalogDetailMode.reserve) return;
    colorId = value;
    final current = selectedVariant;
    if (current == null) {
      final variants = product.variants.where((item) => item.colorId == value);
      final next = variants
          .where((item) => item.availableTotal > 0)
          .firstOrNull;
      final fallback = next ?? variants.firstOrNull;
      sizeId = fallback?.sizeId;
    }
    _adjustAfterSelection();
  }

  void selectSize(int value) {
    if (mode == CatalogDetailMode.reserve) return;
    sizeId = value;
    _adjustAfterSelection();
  }

  void selectBranch(int value) {
    if (mode == CatalogDetailMode.reserve) return;
    if (!branchesWithStock.any((row) => row.branchId == value)) return;
    branchId = value;
    _clearActionFeedback();
    notifyListeners();
  }

  void setQuantity(int value) {
    if (mode == CatalogDetailMode.reserve) return;
    quantity = value;
    error = null;
    cartConflict = null;
    notifyListeners();
  }

  void enterReservation() {
    if (actionBlockReason != null) return;
    final now = DateTime.now();
    if (visitAt == null) {
      final tomorrow = now.add(const Duration(days: 1));
      visitAt = DateTime(tomorrow.year, tomorrow.month, tomorrow.day, 10);
    }
    error = null;
    success = null;
    cartConflict = null;
    mode = CatalogDetailMode.reserve;
    notifyListeners();
  }

  void leaveReservation() {
    mode = CatalogDetailMode.choose;
    error = null;
    notifyListeners();
  }

  void setVisitAt(DateTime value) {
    visitAt = value.toLocal();
    error = null;
    notifyListeners();
  }

  void setNotes(String value) {
    notes = value;
    notifyListeners();
  }

  Future<void> createReservation() async {
    final variant = selectedVariant;
    final visit = visitAt;
    if (variant == null || actionBlockReason != null) return;
    if (visit == null || !visit.isAfter(DateTime.now())) {
      error = 'Elige una fecha y hora futuras para tu visita.';
      notifyListeners();
      return;
    }

    loading = true;
    error = null;
    success = null;
    notifyListeners();
    try {
      final reservation = await api.createReservation(
        ReservationRequest(
          branchId: branchId!,
          visitAt: visit,
          variantId: variant.id,
          quantity: quantity,
          notes: notes.trim(),
        ),
      );
      loading = false;
      mode = CatalogDetailMode.choose;
      successRoute = 'reservations';
      success =
          'Reserva #R-${reservation.id} confirmada en '
          '${reservation.branchName ?? selectedBranchName ?? 'la sucursal'}.';
      notifyListeners();
    } on ApiError catch (caught) {
      loading = false;
      error = caught.message;
      notifyListeners();
    } catch (caught) {
      loading = false;
      error = '$caught';
      notifyListeners();
    }
  }

  Future<void> addToCart({bool confirmBranchChange = false}) async {
    final variant = selectedVariant;
    if (variant == null || branchId == null || actionBlockReason != null) {
      return;
    }

    loading = true;
    error = null;
    success = null;
    notifyListeners();
    try {
      final current = await api.fetchCart();
      if (current != null &&
          current.branchId != branchId &&
          current.detail.isNotEmpty &&
          !confirmBranchChange) {
        loading = false;
        cartConflict = CartBranchConflict(
          from: current.branchName ?? 'otra sucursal',
          to: selectedBranchName ?? 'la sucursal elegida',
        );
        notifyListeners();
        return;
      }

      if (current == null || current.branchId != branchId) {
        await api.openCart(branchId: branchId!);
      }
      final cart = await api.addCartItem(
        variantId: variant.id,
        quantity: quantity,
      );
      loading = false;
      cartConflict = null;
      successRoute = 'cart';
      success =
          'Agregado al carrito. Llevas ${cart.units} '
          '${cart.units == 1 ? 'prenda' : 'prendas'} por '
          'Bs ${formatBolivianos(cart.total)}, desde '
          '${cart.branchName ?? selectedBranchName ?? 'la sucursal'}.';
      final eventSink = aiEventSink;
      if (eventSink != null) {
        unawaited(
          _bestEffortEvent(
            eventSink,
            productId: product.id,
            eventType: 'carrito',
          ),
        );
      }
      notifyListeners();
    } on ApiError catch (caught) {
      loading = false;
      error = caught.message;
      notifyListeners();
    } catch (caught) {
      loading = false;
      error = '$caught';
      notifyListeners();
    }
  }

  void _initializeSelection() {
    final initial =
        product.variants
            .where((variant) => variant.availableTotal > 0)
            .firstOrNull ??
        product.variants.firstOrNull;
    colorId = initial?.colorId;
    sizeId = initial?.sizeId;
    _selectBestBranch();
  }

  void _adjustAfterSelection() {
    _clearActionFeedback();
    final currentBranch = branchId;
    if (currentBranch == null ||
        !branchesWithStock.any((row) => row.branchId == currentBranch)) {
      _selectBestBranch();
    }
    if (quantity > selectedBranchAvailability &&
        selectedBranchAvailability > 0) {
      quantity = selectedBranchAvailability;
    }
    notifyListeners();
  }

  void _selectBestBranch() {
    final available = branchesWithStock;
    final preferred = preferredBranchId;
    branchId = available.any((row) => row.branchId == preferred)
        ? preferred
        : available.firstOrNull?.branchId;
  }

  void _clearActionFeedback() {
    error = null;
    success = null;
    successRoute = null;
    cartConflict = null;
  }

  Future<void> _bestEffortEvent(
    AiEventSink sink, {
    required int productId,
    required String eventType,
  }) async {
    try {
      await sink.reportProductEvent(productId: productId, eventType: eventType);
    } catch (_) {
      // Analytics failures must not affect cart actions.
    }
  }
}
