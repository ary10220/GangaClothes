import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/purchase_history/purchase_history_service.dart';

void main() {
  test('fetches customer purchases from the authenticated endpoint', () async {
    final api = _FakePurchaseApi();
    final purchases = await PurchaseHistoryService(api).fetchPurchases();

    expect(purchases.single.id, 7);
    expect(purchases.single.status, 'pagada');
    expect(api.path, '/ventas/mias');
    expect(api.method, 'GET');
  });

  test('rejects a response that is not a list', () async {
    final api = _FakePurchaseApi(data: <String, dynamic>{});

    expect(
      () => PurchaseHistoryService(api).fetchPurchases(),
      throwsA(isA<FormatException>()),
    );
  });
}

class _FakePurchaseApi extends ApiClient {
  _FakePurchaseApi({this.data}) : super(dio: Dio());

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
    final body = data ?? this.data ?? <Object?>[_purchase()];
    return Response<T>(
      requestOptions: RequestOptions(path: requestPath),
      data: body as T,
      statusCode: 200,
    );
  }
}

Map<String, dynamic> _purchase() => {
  'id': 7,
  'estado': 'pagada',
  'canal': 'web',
  'fecha': null,
  'sucursal_id': 2,
  'sucursal': 'Centro',
  'cliente': null,
  'cajero': null,
  'reserva_id': null,
  'unidades': 1,
  'subtotal': 80,
  'descuento': 0,
  'total': 80,
  'nro_comprobante': null,
  'detalle': <Object?>[],
  'pagos': <Object?>[],
};
