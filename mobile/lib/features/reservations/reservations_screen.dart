import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../features/auth/session_model.dart';
import '../../shared/widgets/gc_app_bar.dart';
import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_chip.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_loading_empty_error.dart';
import '../../shared/widgets/gc_status_badge.dart';
import 'reservation_controller.dart';
import 'reservation_models.dart';
import 'reservation_service.dart';

class ReservationsScreen extends StatefulWidget {
  const ReservationsScreen({
    this.apiClient,
    this.reservationService,
    required this.session,
    this.onLogout,
    super.key,
  });

  final ApiClient? apiClient;
  final ReservationDataSource? reservationService;
  final Session? session;
  final VoidCallback? onLogout;

  @override
  State<ReservationsScreen> createState() => _ReservationsScreenState();
}

class _ReservationsScreenState extends State<ReservationsScreen> {
  late final ReservationController _controller;

  @override
  void initState() {
    super.initState();
    final source =
        widget.reservationService ??
        ReservationService(
          widget.apiClient ??
              (throw StateError('Reservations API is required')),
        );
    _controller = ReservationController(api: source)..addListener(_onChanged);
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
          const Text('MIS RESERVAS', style: GangaTextStyles.eyebrow),
          const SizedBox(height: 5),
          const Text(
            'Prendas apartadas para probartelas en tienda',
            style: GangaTextStyles.heading,
          ),
          const SizedBox(height: 14),
          _buildControls(),
          if (_controller.feedback != null) ...[
            const SizedBox(height: 14),
            GcFeedback(
              message: _controller.feedback!,
              variant: _controller.feedbackIsError
                  ? GcFeedbackVariant.error
                  : GcFeedbackVariant.success,
            ),
          ],
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
            selected: true,
            onPressed: () {},
          ),
        if (customer)
          GcAppBarDestination(
            label: 'Mis compras',
            onPressed: () =>
                Navigator.of(context).pushNamed(AppRoutes.purchaseHistory),
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

  Widget _buildControls() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Wrap(
        spacing: 7,
        runSpacing: 7,
        children: [
          GcChip(
            label: 'Activas (${_controller.activeCount})',
            selected: _controller.filter == ReservationFilter.active,
            onTap: () => _controller.setFilter(ReservationFilter.active),
          ),
          GcChip(
            label: 'Todas (${_controller.allCount})',
            selected: _controller.filter == ReservationFilter.all,
            onTap: () => _controller.setFilter(ReservationFilter.all),
          ),
        ],
      ),
      const SizedBox(height: 10),
      GcButton(
        label: '+ Reservar otra prenda',
        variant: GcButtonVariant.primary,
        onPressed: () => Navigator.of(context).pushNamed(AppRoutes.catalog),
      ),
    ],
  );

  Widget _buildContent() {
    if (_controller.loading && _controller.reservations.isEmpty) {
      return const GcLoadingEmptyError(state: GcPanelState.loading);
    }
    if (_controller.error != null && _controller.reservations.isEmpty) {
      return GcLoadingEmptyError(
        state: GcPanelState.error,
        errorTitle: 'No se pudieron cargar tus reservas',
        errorMessage: _controller.error!.message,
        retryLabel: 'Reintentar',
        onRetry: _controller.load,
      );
    }
    if (_controller.reservations.isEmpty) {
      return Column(
        children: [
          const GcLoadingEmptyError(
            state: GcPanelState.empty,
            emptyTitle: 'Todavia no reservaste prendas.',
            emptyMessage:
                'Elige una en el catalogo y toca «Reservar para probar en tienda».',
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
    final visible = _controller.visibleReservations;
    if (visible.isEmpty) {
      return Column(
        children: [
          const GcLoadingEmptyError(
            state: GcPanelState.empty,
            emptyTitle: 'No tienes reservas activas.',
          ),
          const SizedBox(height: 10),
          GcButton(
            label: 'Ver todas',
            variant: GcButtonVariant.outlined,
            onPressed: () => _controller.setFilter(ReservationFilter.all),
          ),
        ],
      );
    }
    return Column(
      children: [
        if (_controller.error != null) ...[
          GcFeedback(
            message: _controller.error!.message,
            variant: GcFeedbackVariant.error,
            actionLabel: 'Reintentar',
            onAction: _controller.load,
          ),
          const SizedBox(height: 12),
        ],
        for (final reservation in visible) ...[
          _ReservationCard(
            reservation: reservation,
            confirming: _controller.confirmingId == reservation.id,
            cancelling: _controller.cancellingId == reservation.id,
            anyCancellation: _controller.cancellingId != null,
            onConfirm: () => _controller.setConfirmation(reservation.id),
            onCancelConfirmation: () => _controller.setConfirmation(null),
            onCancel: () => _controller.cancel(reservation),
          ),
          const SizedBox(height: 12),
        ],
      ],
    );
  }
}

class _ReservationCard extends StatelessWidget {
  const _ReservationCard({
    required this.reservation,
    required this.confirming,
    required this.cancelling,
    required this.anyCancellation,
    required this.onConfirm,
    required this.onCancelConfirmation,
    required this.onCancel,
  });

  final Reservation reservation;
  final bool confirming;
  final bool cancelling;
  final bool anyCancellation;
  final VoidCallback onConfirm;
  final VoidCallback onCancelConfirmation;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) => Opacity(
    opacity: reservation.isActive ? 1 : .75,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 13, 14, 14),
        child: Semantics(
          container: true,
          label: 'Reserva R-${reservation.id}, ${reservation.status}',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Text(
                      '#R-${reservation.id}',
                      style: GangaTextStyles.metadata,
                    ),
                  ),
                  GcStatusBadge(
                    text: reservation.status,
                    variant: _statusVariant(reservation.status),
                    semanticLabel:
                        'Estado ${reservation.status}. ${ReservationStatus.explanation(reservation.status)}',
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                formatAppointment(reservation.appointmentRaw),
                style: GangaTextStyles.subheading,
              ),
              const SizedBox(height: 2),
              Text(
                reservation.branch,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              Text(
                ReservationStatus.explanation(reservation.status),
                style: const TextStyle(
                  color: GangaColors.gray,
                  fontSize: 12,
                  height: 1.45,
                ),
              ),
              if (isOverdueActive(reservation)) ...[
                const SizedBox(height: 4),
                const Text(
                  'La hora de la cita ya paso.',
                  style: TextStyle(
                    color: GangaColors.alert,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
              const SizedBox(height: 8),
              const Divider(),
              for (final detail in reservation.details)
                _DetailRow(detail: detail),
              if (reservation.notes != null) ...[
                const SizedBox(height: 8),
                Text(
                  '«${reservation.notes}»',
                  style: const TextStyle(
                    color: GangaColors.gray,
                    fontSize: 12,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
              const SizedBox(height: 8),
              Text(
                'reservada el ${formatCreation(reservation.createdAtRaw)}',
                style: GangaTextStyles.metadata,
              ),
              if (reservation.isActive) ...[
                const SizedBox(height: 12),
                if (confirming)
                  _ConfirmationActions(
                    cancelling: cancelling,
                    anyCancellation: anyCancellation,
                    onCancelConfirmation: onCancelConfirmation,
                    onCancel: onCancel,
                  )
                else
                  GcButton(
                    label: 'Cancelar reserva',
                    variant: GcButtonVariant.danger,
                    onPressed: anyCancellation ? null : onConfirm,
                  ),
              ],
            ],
          ),
        ),
      ),
    ),
  );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.detail});

  final ReservationDetail detail;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text('${detail.garment} · ${detail.size} · ${detail.color}'),
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

class _ConfirmationActions extends StatelessWidget {
  const _ConfirmationActions({
    required this.cancelling,
    required this.anyCancellation,
    required this.onCancelConfirmation,
    required this.onCancel,
  });

  final bool cancelling;
  final bool anyCancellation;
  final VoidCallback onCancelConfirmation;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) => Wrap(
    crossAxisAlignment: WrapCrossAlignment.center,
    spacing: 8,
    runSpacing: 8,
    children: [
      const Text(
        '¿Cancelar la reserva?',
        style: TextStyle(fontWeight: FontWeight.w600),
      ),
      GcButton(
        label: 'No',
        variant: GcButtonVariant.outlined,
        onPressed: anyCancellation ? null : onCancelConfirmation,
      ),
      GcButton(
        label: cancelling ? 'Cancelando…' : 'Sí, cancelar',
        variant: GcButtonVariant.danger,
        loading: cancelling,
        onPressed: anyCancellation && !cancelling ? null : onCancel,
      ),
    ],
  );
}

GcStatusBadgeVariant _statusVariant(String status) => switch (status) {
  ReservationStatus.pending => GcStatusBadgeVariant.brand,
  ReservationStatus.prepared ||
  ReservationStatus.attended => GcStatusBadgeVariant.success,
  ReservationStatus.cancelled ||
  ReservationStatus.expired => GcStatusBadgeVariant.neutral,
  _ => GcStatusBadgeVariant.neutral,
};
