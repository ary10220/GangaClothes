import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../features/auth/session_model.dart';
import '../../features/purchase_history/purchase_history_screen.dart';
import '../../features/purchase_history/purchase_receipt_pdf.dart';
import '../../features/purchase_history/purchase_history_service.dart';
import '../../shared/widgets/gc_app_bar.dart';
import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_loading_empty_error.dart';
import '../../shared/widgets/gc_status_badge.dart';
import 'cart_controller.dart';
import 'cart_models.dart';
import 'cart_service.dart';
import '../delivery/delivery_sheet.dart';
import 'payment_sheet.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({
    required this.apiClient,
    required this.session,
    this.controller,
    this.purchaseReceiptService,
    this.purchaseReceiptPdfService,
    this.receiptPdfPrinter,
    this.openPayment = false,
    this.onLogout,
    super.key,
  });

  final ApiClient apiClient;
  final Session? session;
  final CartController? controller;
  final PurchaseReceiptDataSource? purchaseReceiptService;
  final PurchaseReceiptPdfDataSource? purchaseReceiptPdfService;
  final ReceiptPdfPrinter? receiptPdfPrinter;
  final bool openPayment;
  final VoidCallback? onLogout;

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  late final CartController _controller;
  late final PurchaseReceiptDataSource _receiptService;
  late final PurchaseReceiptPdfDataSource? _receiptPdfService;
  bool _autoPaymentOpened = false;
  bool _receiptLoading = false;

  @override
  void initState() {
    super.initState();
    _controller =
        widget.controller ?? CartController(api: CartService(widget.apiClient));
    _receiptService =
        widget.purchaseReceiptService ??
        PurchaseHistoryService(widget.apiClient);
    _receiptPdfService =
        widget.purchaseReceiptPdfService ??
        PurchaseHistoryService(widget.apiClient);
    _controller.addListener(_onChanged);
    _controller.load();
  }

  @override
  void dispose() {
    _controller.removeListener(_onChanged);
    if (widget.controller == null) _controller.dispose();
    super.dispose();
  }

  void _onChanged() {
    if (!mounted) return;
    setState(() {});
    if (widget.openPayment &&
        !_autoPaymentOpened &&
        !_controller.loading &&
        _controller.canPay) {
      _autoPaymentOpened = true;
      WidgetsBinding.instance.addPostFrameCallback((_) => _openPayment());
    }
  }

  void _openPayment() {
    if (!_controller.canPay || !mounted) return;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: GangaColors.white,
      builder: (_) => PaymentSheet(
        controller: _controller,
        initialHolder: widget.session?.user.fullName ?? '',
      ),
    );
  }

  void _openDelivery() {
    if (!_controller.canEditDelivery || !mounted) return;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: GangaColors.white,
      builder: (_) => DeliverySheet(controller: _controller),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: GcAppBar(
      destinations: [
        GcAppBarDestination(
          label: 'Catálogo',
          onPressed: () => Navigator.of(context).pushNamed(AppRoutes.catalog),
        ),
        GcAppBarDestination(
          label: 'Reservas',
          onPressed: () =>
              Navigator.of(context).pushNamed(AppRoutes.reservations),
        ),
        GcAppBarDestination(
          label: 'Mis compras',
          onPressed: () =>
              Navigator.of(context).pushNamed(AppRoutes.purchaseHistory),
        ),
        GcAppBarDestination(
          label: 'Seguimiento',
          onPressed: () =>
              Navigator.of(context).pushNamed(AppRoutes.shipmentTracking),
        ),
        GcAppBarDestination(label: 'Carrito', selected: true, onPressed: () {}),
      ],
      accountName: widget.session?.user.fullName,
      accountRole: widget.session?.user.roles.firstOrNull,
      onLogout: widget.onLogout,
    ),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 16, 14, 36),
        children: [
          const Text('CARRITO', style: GangaTextStyles.eyebrow),
          const SizedBox(height: 5),
          const Text('Compra en línea', style: GangaTextStyles.heading),
          const SizedBox(height: 14),
          if (_controller.feedback != null) ...[
            GcFeedback(
              message: _controller.feedback!,
              variant: _controller.feedbackIsError
                  ? GcFeedbackVariant.error
                  : GcFeedbackVariant.success,
            ),
            const SizedBox(height: 12),
          ],
          _buildContent(),
        ],
      ),
    ),
  );

  Widget _buildContent() {
    final receipt = _controller.receipt;
    if (receipt != null) return _buildReceipt(receipt);
    if (_controller.loading && _controller.cart == null) {
      return const GcLoadingEmptyError(state: GcPanelState.loading);
    }
    if (_controller.error != null && _controller.cart == null) {
      return GcLoadingEmptyError(
        state: GcPanelState.error,
        errorTitle: 'No se pudo cargar tu carrito',
        errorMessage: _controller.error!.message,
        retryLabel: 'Reintentar',
        onRetry: _controller.load,
      );
    }
    final cart = _controller.cart;
    if (cart == null || cart.isEmpty) {
      return Column(
        children: [
          const GcLoadingEmptyError(
            state: GcPanelState.empty,
            emptyTitle: 'Tu carrito está vacío.',
            emptyMessage:
                'Elige prendas en el catálogo y toca «Agregar al carrito».',
          ),
          const SizedBox(height: 10),
          GcButton(
            label: 'Ir al catálogo',
            expand: true,
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.catalog),
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final line in cart.lines) ...[
          _buildLine(cart, line),
          const SizedBox(height: 12),
        ],
        _buildSummary(cart),
      ],
    );
  }

  Widget _buildLine(Cart cart, CartLine line) {
    final busy = _controller.isLineBusy(line.id);
    final insufficient = line.hasInsufficientStock;
    return Card(
      color: insufficient ? GangaColors.lightError : null,
      child: Padding(
        padding: const EdgeInsets.all(13),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    line.garment,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Text(
                  'Bs ${formatCartMoney(line.subtotal)}',
                  style: GangaTextStyles.money,
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${line.size} · ${line.color} · ${line.sku}',
              style: GangaTextStyles.metadata,
            ),
            const SizedBox(height: 8),
            if (line.hasPromotion) ...[
              Text(
                line.promotion?.displayName ?? 'Promoción aplicada',
                style: const TextStyle(
                  color: GangaColors.success,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 3),
            ],
            Row(
              children: [
                Text(
                  'Precio unitario · Bs ${formatCartMoney(line.finalPrice)}',
                  style: GangaTextStyles.metadata,
                ),
                if (line.hasPromotion) ...[
                  const SizedBox(width: 8),
                  Text(
                    'Bs ${formatCartMoney(line.unitPrice)}',
                    style: GangaTextStyles.metadata.copyWith(
                      decoration: TextDecoration.lineThrough,
                    ),
                  ),
                ],
              ],
            ),
            if (line.hasPromotion && line.discount != null) ...[
              const SizedBox(height: 3),
              Text(
                'Ahorrás Bs ${formatCartMoney(line.discount)}',
                style: GangaTextStyles.metadata.copyWith(
                  color: GangaColors.success,
                ),
              ),
            ],
            if (insufficient) ...[
              const SizedBox(height: 8),
              GcStatusBadge(
                text: 'Stock insuficiente',
                variant: GcStatusBadgeVariant.error,
                semanticLabel:
                    'Stock insuficiente: solo hay ${line.available ?? 0} disponibles',
              ),
              const SizedBox(height: 5),
              Text(
                'Solo hay ${line.available ?? 0} en ${cart.branchName ?? 'la sucursal elegida'}.',
                style: const TextStyle(color: GangaColors.alert, fontSize: 12),
              ),
            ],
            const SizedBox(height: 10),
            Row(
              children: [
                _quantityButton(
                  label: 'Quitar una unidad de ${line.garment}',
                  text: '−',
                  enabled:
                      !busy &&
                      !_controller.paymentProcessing &&
                      line.quantity > 1,
                  onPressed: () =>
                      _controller.updateQuantity(line, line.quantity - 1),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 13),
                  child: Semantics(
                    label: 'Cantidad ${line.quantity}',
                    child: Text(
                      '${line.quantity}',
                      style: GangaTextStyles.metadata,
                    ),
                  ),
                ),
                _quantityButton(
                  label: 'Agregar una unidad de ${line.garment}',
                  text: '+',
                  enabled:
                      !busy &&
                      !_controller.paymentProcessing &&
                      !line.hasInsufficientStock &&
                      (line.available == null ||
                          line.quantity < line.available!),
                  onPressed: () =>
                      _controller.updateQuantity(line, line.quantity + 1),
                ),
                const Spacer(),
                TextButton(
                  onPressed: busy || _controller.paymentProcessing
                      ? null
                      : () => _controller.removeLine(line),
                  child: Text(busy ? 'Actualizando…' : 'Quitar'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _quantityButton({
    required String label,
    required String text,
    required bool enabled,
    required VoidCallback onPressed,
  }) => Semantics(
    button: true,
    label: label,
    child: IconButton(
      onPressed: enabled ? onPressed : null,
      tooltip: label,
      icon: Text(text, style: const TextStyle(fontSize: 20)),
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
    ),
  );

  Widget _buildSummary(Cart cart) {
    final branchItems = _controller.branches
        .map(
          (branch) =>
              DropdownMenuItem<int>(value: branch.id, child: Text(branch.name)),
        )
        .toList(growable: false);
    final hasCurrentBranch = _controller.branches.any(
      (branch) => branch.id == cart.branchId,
    );
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('RESUMEN', style: GangaTextStyles.eyebrow),
            const SizedBox(height: 8),
            if (branchItems.isNotEmpty && hasCurrentBranch)
              DropdownButtonFormField<int>(
                initialValue: cart.branchId,
                decoration: const InputDecoration(
                  labelText: 'Sucursal de despacho',
                ),
                items: branchItems,
                onChanged:
                    _controller.branchChanging || _controller.paymentProcessing
                    ? null
                    : (value) {
                        if (value != null && value != cart.branchId) {
                          _controller.changeBranch(value);
                        }
                      },
              )
            else
              Text(
                'Sucursal de despacho: ${cart.branchName ?? 'No disponible'}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            const SizedBox(height: 8),
            Text(
              cart.deliveryType == 'delivery'
                  ? 'Entrega a domicilio'
                  : 'Retiro en sucursal',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            if (cart.deliveryType == 'delivery' && cart.shipment != null) ...[
              if (cart.shipment?.contactPhone != null)
                Text(
                  'Teléfono: ${cart.shipment!.contactPhone}',
                  style: GangaTextStyles.metadata,
                ),
              if (cart.shipment?.latitude != null &&
                  cart.shipment?.longitude != null)
                Text(
                  'Coordenadas: ${cart.shipment!.latitude}, ${cart.shipment!.longitude}',
                  style: GangaTextStyles.metadata,
                ),
              if (cart.shipment?.express == true)
                const Text('Entrega express', style: GangaTextStyles.metadata),
              if (cart.shipment?.distanceKm != null)
                Text(
                  'Distancia backend: ${cart.shipment!.distanceKm} km',
                  style: GangaTextStyles.metadata,
                ),
              if (cart.shipment?.estimatedAt != null)
                Text(
                  'Tiempo estimado backend: ${cart.shipment!.estimatedAt}',
                  style: GangaTextStyles.metadata,
                ),
            ],
            if (cart.shippingCost != null)
              _totalRow('Envío', cart.shippingCost!),
            if (cart.shipment?.address != null) ...[
              const SizedBox(height: 3),
              Text(
                'Dirección: ${cart.shipment!.address}',
                style: GangaTextStyles.metadata,
              ),
              if (cart.shipment?.reference != null)
                Text(
                  'Referencia: ${cart.shipment!.reference}',
                  style: GangaTextStyles.metadata,
                ),
            ],
            const SizedBox(height: 5),
            const Text(
              'El stock se toma de esta sucursal.',
              style: TextStyle(color: GangaColors.gray, fontSize: 11.5),
            ),
            const SizedBox(height: 10),
            GcButton(
              label: cart.deliveryType == 'delivery'
                  ? 'Editar entrega'
                  : 'Elegir entrega a domicilio',
              expand: true,
              variant: GcButtonVariant.outlined,
              onPressed: _controller.canEditDelivery ? _openDelivery : null,
            ),
            const Divider(height: 22),
            _totalRow(
              '${cart.units} ${cart.units == 1 ? 'prenda' : 'prendas'}',
              cart.subtotal,
            ),
            _totalRow('Descuento', cart.discount),
            _totalRow('Total', cart.total, strong: true),
            if (cart.hasInsufficientStock) ...[
              const SizedBox(height: 8),
              const GcFeedback(
                message:
                    'Hay prendas sin stock suficiente. Baja la cantidad, quítalas o elige otra sucursal.',
                variant: GcFeedbackVariant.error,
              ),
            ],
            const SizedBox(height: 12),
            GcButton(
              label: 'Pagar Bs ${formatCartMoney(cart.total)}',
              expand: true,
              loading: _controller.paymentProcessing,
              onPressed: _controller.canPay ? _openPayment : null,
            ),
            const SizedBox(height: 8),
            GcButton(
              label: '← Seguir comprando',
              expand: true,
              variant: GcButtonVariant.outlined,
              onPressed: () =>
                  Navigator.of(context).pushNamed(AppRoutes.catalog),
            ),
          ],
        ),
      ),
    );
  }

  Widget _totalRow(String label, double amount, {bool strong = false}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: strong
                  ? const TextStyle(fontWeight: FontWeight.w800)
                  : null,
            ),
            Text(
              'Bs ${formatCartMoney(amount)}',
              style: strong
                  ? GangaTextStyles.money.copyWith(fontSize: 15)
                  : GangaTextStyles.metadata,
            ),
          ],
        ),
      );

  Widget _buildReceipt(PaymentResult result) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('COMPRA CONFIRMADA', style: GangaTextStyles.eyebrow),
          const SizedBox(height: 4),
          const Text(
            '¡Gracias por tu compra!',
            style: GangaTextStyles.subheading,
          ),
          const SizedBox(height: 8),
          Text(
            'Comprobante ${result.receiptNumber ?? '—'} · se despacha desde ${result.sale.branchName ?? 'la sucursal elegida'}.',
          ),
          const Divider(height: 24),
          for (final line in result.sale.lines)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      '${line.garment} · ${line.size} · ${line.color} ×${line.quantity}',
                    ),
                  ),
                  Text(
                    'Bs ${formatCartMoney(line.subtotal)}',
                    style: GangaTextStyles.metadata,
                  ),
                ],
              ),
            ),
          const Divider(height: 24),
          _totalRow('Total pagado', result.sale.total, strong: true),
          const SizedBox(height: 7),
          Text(
            'Referencia de la pasarela · ${result.externalReference ?? '—'}',
            style: GangaTextStyles.eyebrow,
          ),
          const SizedBox(height: 6),
          Text(
            'Método de pago · ${result.paymentLabel ?? 'Tarjeta'}',
            style: GangaTextStyles.eyebrow,
          ),
          const SizedBox(height: 14),
          GcButton(
            label: _receiptLoading
                ? 'Cargando comprobante…'
                : 'Ver comprobante autenticado',
            expand: true,
            variant: GcButtonVariant.outlined,
            loading: _receiptLoading,
            onPressed: _receiptLoading
                ? null
                : () => _openAuthenticatedReceipt(result.sale.id),
          ),
          const SizedBox(height: 8),
          GcButton(
            label: 'Seguir comprando',
            expand: true,
            onPressed: () {
              _controller.clearReceiptAndReload();
              Navigator.of(context).pushNamed(AppRoutes.catalog);
            },
          ),
        ],
      ),
    ),
  );

  Future<void> _openAuthenticatedReceipt(int saleId) async {
    setState(() => _receiptLoading = true);
    try {
      final receipt = await _receiptService.fetchReceipt(saleId);
      if (!mounted) return;
      setState(() => _receiptLoading = false);
      await showDialog<void>(
        context: context,
        builder: (_) => PurchaseReceiptDialog(
          receipt: receipt,
          onPdfPressed: _receiptPdfService == null
              ? null
              : () => _printReceiptPdf(saleId),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo cargar el comprobante: $error')),
      );
    } finally {
      if (mounted) setState(() => _receiptLoading = false);
    }
  }

  Future<void> _printReceiptPdf(int saleId) async {
    final source = _receiptPdfService;
    if (source == null) return;
    final bytes = await source.fetchReceiptPdf(saleId);
    await printReceiptPdf(bytes, printer: widget.receiptPdfPrinter);
  }
}
