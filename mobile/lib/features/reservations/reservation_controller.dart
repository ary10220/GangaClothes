import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import 'reservation_models.dart';
import 'reservation_service.dart';

enum ReservationFilter { active, all }

class ReservationController extends ChangeNotifier {
  ReservationController({required this.api});

  final ReservationDataSource api;

  List<Reservation> reservations = const [];
  ReservationFilter filter = ReservationFilter.active;
  ApiError? error;
  String? feedback;
  bool feedbackIsError = false;
  int? confirmingId;
  int? cancellingId;
  bool loading = false;

  int get activeCount =>
      reservations.where((reservation) => reservation.isActive).length;

  int get allCount => reservations.length;

  List<Reservation> get visibleReservations =>
      filter == ReservationFilter.active
      ? reservations
            .where((reservation) => reservation.isActive)
            .toList(growable: false)
      : reservations;

  Future<void> load({bool clearFeedback = true}) async {
    loading = true;
    error = null;
    if (clearFeedback) feedback = null;
    _notify();
    try {
      final result = await api.fetchReservations();
      reservations = result;
      loading = false;
      _notify();
    } catch (caught) {
      loading = false;
      error = _asApiError(caught, 'No se pudieron cargar tus reservas.');
      _notify();
    }
  }

  void setFilter(ReservationFilter value) {
    if (filter == value) return;
    filter = value;
    confirmingId = null;
    _notify();
  }

  void setConfirmation(int? reservationId) {
    if (cancellingId != null) return;
    confirmingId = confirmingId == reservationId ? null : reservationId;
    _notify();
  }

  Future<void> cancel(Reservation reservation) async {
    if (!reservation.isActive || cancellingId != null) return;
    cancellingId = reservation.id;
    feedback = null;
    error = null;
    _notify();
    try {
      // The API response is authoritative. Do not synthesize a cancelled copy.
      final updated = await api.cancelReservation(reservation.id);
      reservations = reservations
          .map((item) => item.id == updated.id ? updated : item)
          .toList(growable: false);
      feedback =
          'Reserva #R-${reservation.id} cancelada. Las prendas vuelven a estar disponibles.';
      feedbackIsError = false;
    } catch (caught) {
      final apiError = _asApiError(caught, 'No se pudo cancelar la reserva.');
      feedback = apiError.message;
      feedbackIsError = true;
      // A 400/403/404 can mean the server state changed while this card was open.
      await load(clearFeedback: false);
    } finally {
      cancellingId = null;
      confirmingId = null;
      _notify();
    }
  }

  void _notify() {
    if (hasListeners) notifyListeners();
  }
}

ApiError _asApiError(Object error, String fallback) {
  if (error is ApiError) return error;
  return ApiError(statusCode: 0, message: fallback, cause: error);
}
