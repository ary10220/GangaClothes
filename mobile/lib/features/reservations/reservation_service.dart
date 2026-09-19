import '../../core/network/api_client.dart';
import 'reservation_models.dart';

abstract interface class ReservationDataSource {
  Future<List<Reservation>> fetchReservations();

  Future<Reservation> cancelReservation(int reservationId);
}

class ReservationService implements ReservationDataSource {
  const ReservationService(this.apiClient);

  final ApiClient apiClient;

  @override
  Future<List<Reservation>> fetchReservations() async {
    final response = await apiClient.request<Object?>('/reservas/mias');
    return _reservations(response.data);
  }

  @override
  Future<Reservation> cancelReservation(int reservationId) async {
    final response = await apiClient.request<Object?>(
      '/reservas/$reservationId/cancelar',
      method: 'POST',
      data: <String, dynamic>{},
    );
    return Reservation.fromJson(_map(response.data));
  }
}

List<Reservation> _reservations(Object? value) {
  if (value is! List) {
    throw const FormatException('Reservation response is not a list');
  }
  return value
      .whereType<Map>()
      .map((item) => Reservation.fromJson(Map<String, dynamic>.from(item)))
      .toList(growable: false);
}

Map<String, dynamic> _map(Object? value) {
  if (value is! Map) throw const FormatException('Expected a JSON object');
  return Map<String, dynamic>.from(value);
}
