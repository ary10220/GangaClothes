import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/delivery/delivery_models.dart';
import 'package:mobile/features/delivery/delivery_service.dart';

void main() {
  test('sends the exact tariff, quote, create, and delete contracts', () async {
    final api = _FakeApi();
    final service = DeliveryService(api);

    await service.fetchDeliveryTariff();
    await service.quoteDelivery(
      const DeliveryQuoteInput(
        branchId: 2,
        latitude: -17.78,
        longitude: -63.18,
        express: true,
      ),
    );
    await service.createDelivery(
      const DeliveryInput(
        saleId: 4,
        address: 'Calle 10 #45',
        reference: 'Portón azul',
        contactPhone: '70000000',
        latitude: -17.78,
        longitude: -63.18,
        express: true,
      ),
    );
    await service.removeDelivery(9);

    expect(api.requests, [
      {
        'path': '/envios/tarifa',
        'method': 'GET',
        'data': null,
        'queryParameters': null,
      },
      {
        'path': '/envios/cotizar',
        'method': 'POST',
        'data': {
          'sucursal_id': 2,
          'latitud': -17.78,
          'longitud': -63.18,
          'express': true,
        },
        'queryParameters': null,
      },
      {
        'path': '/envios',
        'method': 'POST',
        'data': {
          'venta_id': 4,
          'direccion': 'Calle 10 #45',
          'referencia': 'Portón azul',
          'telefono_contacto': '70000000',
          'latitud': -17.78,
          'longitud': -63.18,
          'express': true,
        },
        'queryParameters': null,
      },
      {
        'path': '/envios/9',
        'method': 'DELETE',
        'data': null,
        'queryParameters': null,
      },
    ]);
    expect(api.requests[1]['data'].toString(), isNot(contains('monto_compra')));
  });
}

class _FakeApi extends ApiClient {
  _FakeApi() : super(dio: Dio());

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
    requests.add({
      'path': path,
      'method': method,
      'data': data,
      'queryParameters': queryParameters,
    });
    final response = switch (path) {
      '/envios/tarifa' => {'cobertura_km': 25},
      '/envios/cotizar' => _quoteJson,
      '/envios' => {
        'envio': {
          'id': 9,
          'estado': 'pendiente',
          'direccion': 'Calle 10 #45',
          'latitud': -17.78,
          'longitud': -63.18,
          'express': true,
        },
        'cotizacion': _quoteJson,
        'venta': _cartJson('delivery', 86.5),
      },
      '/envios/9' => _cartJson('sucursal', 80),
      _ => <String, dynamic>{},
    };
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
      statusCode: 200,
    );
  }
}

final _quoteJson = <String, dynamic>{
  'dentro_de_cobertura': true,
  'mensaje_cobertura': null,
  'desglose': [
    {'concepto': 'Base', 'importe': 12},
    {'concepto': 'Envío gratis', 'importe': -18.5},
  ],
  'costo_envio': 0,
  'distancia_km': 2.5,
  'minutos_estimados': 55,
  'entrega_estimada': '2026-09-21T10:00:00',
  'express': true,
  'sucursal': {
    'id': 2,
    'nombre': 'Centro',
    'latitud': -17.78,
    'longitud': -63.18,
  },
  'destino': {'latitud': -17.78, 'longitud': -63.18},
  'total_a_pagar': 80,
};

Map<String, dynamic> _cartJson(String type, double total) => {
  'id': 4,
  'estado': 'carrito',
  'sucursal_id': 2,
  'sucursal': 'Centro',
  'unidades': 1,
  'subtotal': 80,
  'descuento': 0,
  'tipo_entrega': type,
  'costo_envio': type == 'delivery' ? 0 : 0,
  'envio': type == 'delivery'
      ? {
          'id': 9,
          'direccion': 'Calle 10 #45',
          'latitud': -17.78,
          'longitud': -63.18,
          'express': true,
        }
      : null,
  'total': total,
  'detalle': [
    {
      'id': 8,
      'variante_id': 9,
      'sku': 'GC-09',
      'prenda': 'Camisa',
      'talla': 'M',
      'color': 'Azul',
      'cantidad': 1,
      'precio_unitario': 80,
      'subtotal': 80,
    },
  ],
};
