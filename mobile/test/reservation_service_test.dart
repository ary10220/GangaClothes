import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/reservations/reservation_models.dart';
import 'package:mobile/features/reservations/reservation_service.dart';

void main() {
  test('loads reservations and sends an empty cancellation body', () async {
    final api = _FakeReservationApi();
    final service = ReservationService(api);

    final reservations = await service.fetchReservations();
    final cancelled = await service.cancelReservation(7);

    expect(reservations.single.id, 7);
    expect(reservations.single.status, ReservationStatus.pending);
    expect(reservations.single.details.single.quantity, 2);
    expect(cancelled.status, ReservationStatus.cancelled);
    expect(api.requests, [
      {'path': '/reservas/mias', 'method': 'GET', 'data': null},
      {
        'path': '/reservas/7/cancelar',
        'method': 'POST',
        'data': <String, dynamic>{},
      },
    ]);
  });

  test(
    'keeps a zone-less appointment local and converts creation to local time',
    () {
      final reservation = Reservation.fromJson({
        'id': 1,
        'estado': 'preparada',
        'fecha_creacion': '2030-04-05T09:07:06Z',
        'fecha_hora_prueba': '2030-04-05T09:07:06',
        'notas': null,
        'sucursal': 'Centro',
        'unidades': 1,
        'detalle': [],
      });

      expect(reservation.appointmentAt?.hour, 9);
      expect(reservation.appointmentAt?.minute, 7);
      expect(
        formatAppointment(reservation.appointmentRaw),
        'vie, 05/04, 09:07',
      );
      expect(formatCreation(reservation.createdAtRaw), isNotEmpty);
    },
  );
}

class _FakeReservationApi extends ApiClient {
  _FakeReservationApi() : super(dio: Dio());

  final requests = <Map<String, Object?>>[];

  @override
  Future<Response<T>> request<T>(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    requests.add({'path': path, 'method': method, 'data': data});
    final response = path == '/reservas/mias'
        ? <dynamic>[_reservation(status: ReservationStatus.pending)]
        : _reservation(status: ReservationStatus.cancelled);
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
      statusCode: 200,
    );
  }
}

Map<String, dynamic> _reservation({required String status}) => {
  'id': 7,
  'estado': status,
  'fecha_creacion': '2030-04-05T09:07:06Z',
  'fecha_hora_prueba': '2030-04-06T10:30:00',
  'notas': 'Probador',
  'sucursal': 'Centro',
  'unidades': 2,
  'detalle': [
    {
      'id': 9,
      'variante_id': 3,
      'sku': 'CAM-03',
      'prenda': 'Camisa',
      'talla': 'M',
      'color': 'Azul',
      'cantidad': 2,
    },
  ],
};
