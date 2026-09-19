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

class PurchaseHistoryScreen extends StatefulWidget {
  const PurchaseHistoryScreen({
    this.apiClient,
    this.purchaseHistoryService,
    required this.session,
    this.onLogout,
    super.key,
  });

  final ApiClient? apiClient;
  final PurchaseHistoryDataSource? purchaseHistoryService;
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
    final source =
        widget.purchaseHistoryService ??
        PurchaseHistoryService(
          widget.apiClient ??
              (throw StateError('Purchase history API is required')),
        );
    _controller = PurchaseHistoryController(api: source)
      ..addListener(_onChanged);
    _controller.load();
  }

  void _onChanged() {
    if (mounted) setState(() {});
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
                child: _PurchaseCard(purchase: purchase),
              ),
          ],
        );
      },
    );
  }
}

class _PurchaseCard extends StatelessWidget {
  const _PurchaseCard({required this.purchase});

  final Purchase purchase;

  @override
  Widget build(BuildContext context) {
    final payment = purchase.successfulPayment;
    final receipt = purchase.receiptNumber?.trim().isNotEmpty == true
        ? purchase.receiptNumber!
        : '#V-${purchase.id}';
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
              Text(
                'Pago: ${purchasePaymentMethod(payment?.method)} · '
                '${purchasePaymentStatus(payment?.status)}',
                style: const TextStyle(color: GangaColors.gray, fontSize: 12),
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
              if (purchase.discount > 0)
                _TotalRow(
                  label: 'Descuento',
                  value: '−Bs ${formatPurchaseMoney(purchase.discount)}',
                ),
              _TotalRow(
                label: 'Total',
                value: 'Bs ${formatPurchaseMoney(purchase.total)}',
                strong: true,
              ),
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
                'Bs ${formatPurchaseMoney(detail.subtotal)}',
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
