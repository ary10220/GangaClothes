import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/catalog/catalog_detail_models.dart';
import 'package:mobile/features/catalog/catalog_detail_service.dart';

void main() {
  test('serializes reservation and cart-entry contracts', () async {
    final api = _FakeApi();
    final service = CatalogActionService(api);
    final visit = DateTime(2030, 4, 5, 9, 7, 6);

    await service.createReservation(
      ReservationRequest(
        branchId: 3,
        visitAt: visit,
        variantId: 8,
        quantity: 2,
        notes: 'Probador',
      ),
    );
    await service.openCart(branchId: 3);
    await service.addCartItem(variantId: 8, quantity: 2);

    expect(api.requests[0], {
      'path': '/reservas',
      'method': 'POST',
      'data': {
        'sucursal_id': 3,
        'fecha_hora_prueba': '2030-04-05T09:07:06',
        'notas': 'Probador',
        'detalle': [
          {'variante_id': 8, 'cantidad': 2},
        ],
      },
    });
    expect(api.requests[1]['data'], {'sucursal_id': 3, 'canal': 'movil'});
    expect(api.requests[2]['data'], {'variante_id': 8, 'cantidad': 2});
  });

  test('treats an absent cart as an empty cart', () async {
    final service = CatalogActionService(_FakeApi(absentCart: true));

    expect(await service.fetchCart(), isNull);
  });
}

class _FakeApi extends ApiClient {
  _FakeApi({this.absentCart = false}) : super(dio: Dio());

  final bool absentCart;
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
    if (path == '/ventas/carrito' && method == 'GET' && absentCart) {
      throw const ApiError(statusCode: 404, message: 'No hay carrito');
    }
    requests.add({'path': path, 'method': method, 'data': data});
    final response = switch (path) {
      '/reservas' => <String, dynamic>{
        'id': 1,
        'sucursal_id': 3,
        'sucursal': 'Centro',
        'fecha_hora_prueba': '2030-04-05T09:07:06',
      },
      _ => {
        'id': 4,
        'sucursal_id': 3,
        'sucursal': 'Centro',
        'unidades': 2,
        'total': 240,
        'detalle': [
          {'id': 5, 'variante_id': 8},
        ],
      },
    };
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
      statusCode: 200,
    );
  }
}
