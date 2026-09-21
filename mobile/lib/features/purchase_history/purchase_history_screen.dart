import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../features/auth/session_model.dart';
import '../../shared/widgets/gc_app_bar.dart';
import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_loading_empty_error.dart';
import '../../shared/widgets/gc_status_badge.dart';
import 'purchase_history_controller.dart';
import 'purchase_history_models.dart';
import 'purchase_history_service.dart';
import 'purchase_receipt_pdf.dart';

class PurchaseHistoryScreen extends StatefulWidget {
  const PurchaseHistoryScreen({
    this.apiClient,
    this.purchaseHistoryService,
    this.purchaseReceiptService,
    this.purchaseReceiptPdfService,
    this.receiptPdfPrinter,
    required this.session,
    this.onLogout,
    super.key,
  });

  final ApiClient? apiClient;
  final PurchaseHistoryDataSource? purchaseHistoryService;
  final PurchaseReceiptDataSource? purchaseReceiptService;
  final PurchaseReceiptPdfDataSource? purchaseReceiptPdfService;
  final ReceiptPdfPrinter? receiptPdfPrinter;
  final Session? session;
  final VoidCallback? onLogout;

  @override
  State<PurchaseHistoryScreen> createState() => _PurchaseHistoryScreenState();
}

class _PurchaseHistoryScreenState extends State<PurchaseHistoryScreen> {
  late final PurchaseHistoryController _controller;

  @override
  void initState() {
    super.initState();
    final PurchaseHistoryDataSource source =
        widget.purchaseHistoryService ??
        PurchaseHistoryService(
          widget.apiClient ??
              (throw StateError('Purchase history API is required')),
        );
    PurchaseReceiptDataSource? receiptSource = widget.purchaseReceiptService;
    if (receiptSource == null && source is PurchaseReceiptDataSource) {
      receiptSource = source as PurchaseReceiptDataSource;
    }
    PurchaseReceiptPdfDataSource? pdfReceiptSource =
        widget.purchaseReceiptPdfService;
    if (pdfReceiptSource == null && source is PurchaseReceiptPdfDataSource) {
      pdfReceiptSource = source as PurchaseReceiptPdfDataSource;
    }
    _controller = PurchaseHistoryController(
      api: source,
      receiptApi: receiptSource,
      pdfReceiptApi: pdfReceiptSource,
    )..addListener(_onChanged);
    _controller.load();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _showReceipt(Purchase purchase) async {
    final receipt = await _controller.loadReceipt(purchase.id);
    if (!mounted) return;
    if (receipt == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _controller.receiptError?.message ??
                'No se pudo cargar el comprobante.',
          ),
        ),
      );
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (_) => PurchaseReceiptDialog(
        receipt: receipt,
        onPdfPressed: _controller.pdfReceiptApi == null
            ? null
            : () => _printReceiptPdf(purchase.id),
      ),
    );
  }

  Future<void> _printReceiptPdf(int purchaseId) async {
    final source = _controller.pdfReceiptApi;
    if (source == null) return;
    final bytes = await source.fetchReceiptPdf(purchaseId);
    await printReceiptPdf(bytes, printer: widget.receiptPdfPrinter);
  }

  @override
  void dispose() {
    _controller
      ..removeListener(_onChanged)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: _buildAppBar(),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(14, 16, 14, 36),
        children: [
          const Text('MIS COMPRAS', style: GangaTextStyles.eyebrow),
          const SizedBox(height: 5),
          const Text(
            'Compras pagadas y comprobantes de tus pedidos',
            style: GangaTextStyles.heading,
          ),
          const SizedBox(height: 14),
          GcButton(
            label: 'Seguir comprando',
            variant: GcButtonVariant.primary,
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.catalog),
          ),
          const SizedBox(height: 16),
          _buildContent(),
        ],
      ),
    ),
  );

  PreferredSizeWidget _buildAppBar() {
    final customer = widget.session?.user.roles.contains('cliente') ?? false;
    return GcAppBar(
      destinations: [
        GcAppBarDestination(
          label: 'Catálogo',
          onPressed: () => Navigator.of(context).pushNamed(AppRoutes.catalog),
        ),
        if (customer)
          GcAppBarDestination(
            label: 'Mis reservas',
            onPressed: () =>
                Navigator.of(context).pushNamed(AppRoutes.reservations),
          ),
        if (customer)
          GcAppBarDestination(
            label: 'Mis compras',
            selected: true,
            onPressed: () {},
          ),
        if (customer)
          GcAppBarDestination(
            label: 'Carrito',
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.cart),
          ),
      ],
      accountName: widget.session?.user.fullName,
      accountRole: widget.session?.user.roles.firstOrNull,
      onAccountPressed: widget.session == null ? null : () {},
      onLogout: widget.session == null ? null : widget.onLogout,
    );
  }

  Widget _buildContent() {
    if (_controller.loading && _controller.purchases.isEmpty) {
      return const GcLoadingEmptyError(state: GcPanelState.loading);
    }
    if (_controller.error != null && _controller.purchases.isEmpty) {
      return GcLoadingEmptyError(
        state: GcPanelState.error,
        errorTitle: 'No se pudieron cargar tus compras',
        errorMessage: _controller.error!.message,
        retryLabel: 'Reintentar',
        onRetry: _controller.load,
      );
    }
    if (_controller.purchases.isEmpty) {
      return Column(
        children: [
          const GcLoadingEmptyError(
            state: GcPanelState.empty,
            emptyTitle: 'Todavia no tienes compras pagadas.',
            emptyMessage:
                'Elige una prenda en el catalogo para comenzar a comprar.',
          ),
          const SizedBox(height: 10),
          GcButton(
            label: 'Ir al catalogo',
            variant: GcButtonVariant.primary,
            onPressed: () => Navigator.of(context).pushNamed(AppRoutes.catalog),
          ),
        ],
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final twoColumns = constraints.maxWidth >= 660;
        final cardWidth = twoColumns
            ? (constraints.maxWidth - 12) / 2
            : constraints.maxWidth;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final purchase in _controller.purchases)
              SizedBox(
                width: cardWidth,
                child: _PurchaseCard(
                  purchase: purchase,
                  onReceiptPressed: _controller.receiptApi == null
                      ? null
                      : () => _showReceipt(purchase),
                  receiptLoading:
                      _controller.receiptLoading &&
                      _controller.receiptPurchaseId == purchase.id,
                ),
              ),
          ],
        );
      },
    );
  }
}

class _PurchaseCard extends StatelessWidget {
  const _PurchaseCard({
    required this.purchase,
    this.onReceiptPressed,
    this.receiptLoading = false,
  });

  final Purchase purchase;
  final VoidCallback? onReceiptPressed;
  final bool receiptLoading;

  @override
  Widget build(BuildContext context) {
    final payment = purchase.successfulPayment;
    final receipt = purchase.displayReceiptNumber;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 13, 14, 14),
        child: Semantics(
          container: true,
          label: 'Compra $receipt, ${purchase.status}',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        Flexible(
                          child: Text(receipt, style: GangaTextStyles.metadata),
                        ),
                        const SizedBox(width: 7),
                        const Text('compra', style: GangaTextStyles.eyebrow),
                      ],
                    ),
                  ),
                  GcStatusBadge(
                    text: purchase.status,
                    variant: GcStatusBadgeVariant.success,
                    semanticLabel: 'Estado ${purchase.status}',
                  ),
                ],
              ),
              const SizedBox(height: 10),
              _InfoText(
                label: 'Comprada',
                value: formatPurchaseDate(purchase.dateRaw),
              ),
              const SizedBox(height: 2),
              _InfoText(
                label: 'Sucursal',
                value: purchase.branchName ?? 'No informada',
              ),
              const SizedBox(height: 7),
              _InfoText(
                label: 'Entrega',
                value: purchase.isDelivery ? 'Delivery' : 'Retiro en sucursal',
              ),
              if (purchase.shippingCost != null)
                _InfoText(
                  label: 'Envío',
                  value: 'Bs ${formatPurchaseMoney(purchase.shippingCost)}',
                ),
              if (purchase.shipment?.address?.trim().isNotEmpty == true)
                _InfoText(
                  label: 'Dirección',
                  value: purchase.shipment!.address!,
                ),
              if (purchase.shipment?.status?.trim().isNotEmpty == true)
                _InfoText(
                  label: 'Estado del envío',
                  value: purchase.shipment!.status!,
                ),
              Text(
                'Pago: ${purchasePaymentMethod(payment?.method)} · '
                '${purchasePaymentStatus(payment?.status)}',
                style: const TextStyle(color: GangaColors.gray, fontSize: 12),
              ),
              if (payment?.externalReference?.trim().isNotEmpty == true)
                _InfoText(
                  label: 'Referencia',
                  value: payment!.externalReference!,
                ),
              const SizedBox(height: 10),
              const Divider(),
              for (final detail in purchase.details) _DetailRow(detail: detail),
              const SizedBox(height: 7),
              const Divider(),
              _TotalRow(
                label:
                    '${purchase.units} ${purchase.units == 1 ? 'unidad' : 'unidades'}',
                value: null,
              ),
              _TotalRow(
                label: 'Subtotal',
                value: 'Bs ${formatPurchaseMoney(purchase.subtotal)}',
              ),
              _TotalRow(
                label: 'Descuento',
                value: '−Bs ${formatPurchaseMoney(purchase.discount)}',
              ),
              _TotalRow(
                label: 'Total',
                value: 'Bs ${formatPurchaseMoney(purchase.total)}',
                strong: true,
              ),
              if (onReceiptPressed != null) ...[
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: receiptLoading ? null : onReceiptPressed,
                    icon: receiptLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.receipt_long_outlined),
                    label: Text(
                      receiptLoading
                          ? 'Cargando comprobante...'
                          : 'Ver comprobante',
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _InfoText extends StatelessWidget {
  const _InfoText({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Text.rich(
    TextSpan(
      style: const TextStyle(
        color: GangaColors.gray,
        fontSize: 12,
        height: 1.5,
      ),
      children: [
        TextSpan(
          text: '$label: ',
          style: const TextStyle(
            color: GangaColors.ink,
            fontWeight: FontWeight.w700,
          ),
        ),
        TextSpan(text: value),
      ],
    ),
  );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.detail});

  final PurchaseDetail detail;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${detail.garment} · ${detail.size} · ${detail.color}'),
              const SizedBox(height: 2),
              Text(
                'Precio final: Bs ${formatPurchaseMoney(detail.finalPrice)} · '
                'lista: Bs ${formatPurchaseMoney(detail.unitPrice)}',
                style: GangaTextStyles.metadata,
              ),
              if (detail.discount != null)
                Text(
                  'Descuento: Bs ${formatPurchaseMoney(detail.discount)}',
                  style: GangaTextStyles.metadata,
                ),
              if (detail.promotion?.displayName?.trim().isNotEmpty == true)
                Text(
                  detail.promotion!.displayName!,
                  style: const TextStyle(
                    color: GangaColors.success,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              Text(
                'Subtotal: Bs ${formatPurchaseMoney(detail.subtotal)}',
                style: GangaTextStyles.metadata,
              ),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '×${detail.quantity}',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ],
    ),
  );
}

class _TotalRow extends StatelessWidget {
  const _TotalRow({
    required this.label,
    required this.value,
    this.strong = false,
  });

  final String label;
  final String? value;
  final bool strong;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 5),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: strong
                ? const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)
                : const TextStyle(color: GangaColors.gray, fontSize: 11.5),
          ),
        ),
        if (value != null)
          Text(
            value!,
            style: strong
                ? const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)
                : const TextStyle(color: GangaColors.gray, fontSize: 11.5),
          ),
      ],
    ),
  );
}

class PurchaseReceiptDialog extends StatefulWidget {
  const PurchaseReceiptDialog({
    required this.receipt,
    this.onPdfPressed,
    super.key,
  });

  final PurchaseReceipt receipt;
  final Future<void> Function()? onPdfPressed;

  @override
  State<PurchaseReceiptDialog> createState() => _PurchaseReceiptDialogState();
}

class _PurchaseReceiptDialogState extends State<PurchaseReceiptDialog> {
  bool _pdfLoading = false;
  String? _pdfError;

  Future<void> _handlePdfPressed() async {
    final callback = widget.onPdfPressed;
    if (callback == null || _pdfLoading) return;
    setState(() {
      _pdfLoading = true;
      _pdfError = null;
    });
    try {
      await callback();
    } catch (error) {
      if (mounted) {
        setState(() => _pdfError = 'No se pudo abrir el PDF: $error');
      }
    } finally {
      if (mounted) setState(() => _pdfLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final receipt = widget.receipt;
    final currency = receipt.currency?.trim().isNotEmpty == true
        ? receipt.currency!
        : 'Bs';
    final receiptNumber = receipt.receiptNumber?.trim().isNotEmpty == true
        ? receipt.receiptNumber!
        : 'Comprobante';
    final payment = receipt.payment;
    final delivery = receipt.delivery;
    return AlertDialog(
      title: Text(receiptNumber),
      content: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            _InfoText(
              label: 'Fecha',
              value: formatPurchaseDate(receipt.dateRaw),
            ),
            if (delivery != null) ...[
              _InfoText(label: 'Entrega', value: delivery.displayType),
              if (delivery.address?.trim().isNotEmpty == true)
                _InfoText(label: 'Dirección', value: delivery.address!),
              if (delivery.branch?.trim().isNotEmpty == true)
                _InfoText(label: 'Sucursal', value: delivery.branch!),
            ],
            if (payment != null)
              _InfoText(
                label: 'Pago',
                value:
                    '${purchasePaymentMethod(payment.method)} · '
                    '${purchasePaymentStatus(payment.status)}',
              ),
            if (payment?.externalReference?.trim().isNotEmpty == true)
              _InfoText(
                label: 'Referencia',
                value: payment!.externalReference!,
              ),
            const SizedBox(height: 10),
            for (final item in receipt.items)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(
                  '${item.garment} · ${item.quantity} · '
                  '$currency ${formatPurchaseMoney(item.subtotal)}',
                ),
              ),
            const Divider(),
            _ReceiptMoneyRow(
              label: 'Subtotal',
              value: '$currency ${formatPurchaseMoney(receipt.subtotal)}',
            ),
            _ReceiptMoneyRow(
              label: 'Descuento',
              value: '$currency ${formatPurchaseMoney(receipt.discount)}',
            ),
            _ReceiptMoneyRow(
              label: 'Envío',
              value: '$currency ${formatPurchaseMoney(receipt.shippingCost)}',
            ),
            _ReceiptMoneyRow(
              label: 'Total',
              value: '$currency ${formatPurchaseMoney(receipt.total)}',
              strong: true,
            ),
            const SizedBox(height: 12),
            if (widget.onPdfPressed != null) ...[
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: _pdfLoading ? null : _handlePdfPressed,
                  icon: _pdfLoading
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.picture_as_pdf_outlined),
                  label: Text(_pdfLoading ? 'Abriendo PDF...' : 'Abrir PDF'),
                ),
              ),
              if (_pdfError != null) ...[
                const SizedBox(height: 6),
                Text(_pdfError!, style: const TextStyle(fontSize: 11.5)),
              ],
            ] else
              const Text(
                'La acción de PDF autenticado no está disponible en este momento.',
                style: TextStyle(fontSize: 11.5),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cerrar'),
        ),
      ],
    );
  }
}

class _ReceiptMoneyRow extends StatelessWidget {
  const _ReceiptMoneyRow({
    required this.label,
    required this.value,
    this.strong = false,
  });

  final String label;
  final String value;
  final bool strong;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 5),
    child: Row(
      children: [
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              fontWeight: strong ? FontWeight.w800 : FontWeight.normal,
            ),
          ),
        ),
        Text(
          value,
          style: TextStyle(fontWeight: strong ? FontWeight.w800 : null),
        ),
      ],
    ),
  );
}
