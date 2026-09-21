import 'dart:async';

import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../features/auth/session_model.dart';
import '../../shared/widgets/gc_app_bar.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_loading_empty_error.dart';
import 'shipment_controller.dart';
import 'shipment_service.dart';
import 'shipment_summary.dart';

class ShipmentTrackingScreen extends StatefulWidget {
  const ShipmentTrackingScreen({
    this.apiClient,
    this.shipmentService,
    required this.session,
    this.shipmentId,
    this.onLogout,
    super.key,
  });

  final ApiClient? apiClient;
  final ShipmentDataSource? shipmentService;
  final Session? session;
  final int? shipmentId;
  final VoidCallback? onLogout;

  @override
  State<ShipmentTrackingScreen> createState() => _ShipmentTrackingScreenState();
}

class _ShipmentTrackingScreenState extends State<ShipmentTrackingScreen> {
  late final ShipmentTrackingController _controller;

  @override
  void initState() {
    super.initState();
    final source =
        widget.shipmentService ??
        ShipmentService(
          widget.apiClient ?? (throw StateError('Shipment API is required')),
        );
    _controller = ShipmentTrackingController(api: source)
      ..addListener(_onChanged);
    unawaited(_controller.load());
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
          const Text('SEGUIMIENTO', style: GangaTextStyles.eyebrow),
          const SizedBox(height: 5),
          const Text(
            'Envíos de compras pagadas',
            style: GangaTextStyles.heading,
          ),
          const SizedBox(height: 6),
          const Text(
            'Los cambios se consultan automáticamente mientras un envío siga activo.',
            style: GangaTextStyles.metadata,
          ),
          if (_controller.error != null &&
              _controller.shipments.isNotEmpty) ...[
            const SizedBox(height: 12),
            GcFeedback(
              message:
                  '${_controller.error!.message} Se conservaron los últimos datos.',
              variant: GcFeedbackVariant.error,
            ),
          ],
          const SizedBox(height: 16),
          _buildContent(),
        ],
      ),
    ),
  );

  PreferredSizeWidget _buildAppBar() => GcAppBar(
    destinations: [
      GcAppBarDestination(
        label: 'Catálogo',
        onPressed: () => Navigator.of(context).pushNamed(AppRoutes.catalog),
      ),
      GcAppBarDestination(
        label: 'Mis reservas',
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
        selected: true,
        onPressed: () {},
      ),
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

  Widget _buildContent() {
    if (_controller.loading && _controller.shipments.isEmpty) {
      return const GcLoadingEmptyError(state: GcPanelState.loading);
    }
    if (_controller.error != null && _controller.shipments.isEmpty) {
      return GcLoadingEmptyError(
        state: GcPanelState.error,
        errorTitle: 'No se pudo cargar el seguimiento',
        errorMessage: _controller.error!.message,
        retryLabel: 'Reintentar',
        onRetry: _controller.load,
      );
    }
    if (_controller.shipments.isEmpty) {
      return const GcLoadingEmptyError(
        state: GcPanelState.empty,
        emptyTitle: 'No hay envíos pagados para mostrar.',
        emptyMessage:
            'El seguimiento estará disponible después de pagar una compra con delivery.',
      );
    }

    final shipments = [..._controller.shipments];
    final focusedId = widget.shipmentId;
    if (focusedId != null) {
      shipments.sort(
        (a, b) =>
            (a.id == focusedId ? 0 : 1).compareTo(b.id == focusedId ? 0 : 1),
      );
    }
    return Column(
      children: [
        if (_controller.loading) const LinearProgressIndicator(),
        for (final shipment in shipments)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: ShipmentSummaryCard(shipment: shipment),
          ),
      ],
    );
  }
}
