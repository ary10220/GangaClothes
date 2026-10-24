import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/shipment_tracking/shipment_service.dart';

void main() {
  test('reads only paid shipments from the authenticated endpoint', () async {
    final api = _FakeShipmentApi([
      _shipment(id: 2, saleState: 'pagada'),
      _shipment(id: 1, saleState: 'pendiente'),
    ]);

    final shipments = await ShipmentService(api).fetchShipments();

    expect(shipments.map((shipment) => shipment.id), [2]);
    expect(api.path, '/envios/mios');
    expect(api.method, 'GET');
  });

  test('rejects a response that is not a list', () async {
    final api = _FakeShipmentApi(const <String, dynamic>{});

    expect(
      () => ShipmentService(api).fetchShipments(),
      throwsA(isA<FormatException>()),
    );
  });
}

class _FakeShipmentApi extends ApiClient {
  _FakeShipmentApi(this.data) : super(dio: Dio());

  final Object? data;
  String? path;
  String? method;

  @override
  Future<Response<T>> request<T>(
    String requestPath, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    path = requestPath;
    this.method = method;
    return Response<T>(
      requestOptions: RequestOptions(path: requestPath),
      data: this.data as T,
      statusCode: 200,
    );
  }
}

Map<String, dynamic> _shipment({required int id, required String saleState}) =>
    {
      'id': id,
      'estado': 'pendiente',
      'etiqueta_estado': 'Pendiente de asignar',
      'activo': true,
      'venta': {'id': id, 'estado': saleState, 'canal': 'movil'},
    };
