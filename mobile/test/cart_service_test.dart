import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/features/cart/cart_models.dart';
import 'package:mobile/features/cart/cart_service.dart';

void main() {
  test(
    'sends the Stripe test-card contract without simulation or CVC fields',
    () async {
      final api = _FakeApi();
      final service = CartService(api);

      await service.changeBranch(3);
      await service.updateQuantity(lineId: 8, quantity: 2);
      await service.removeLine(8);
      await service.confirmCart();
      await service.pay(saleId: 4, amount: 80, cardNumber: '4242424242424242');

      expect(api.requests.map((request) => request['path']), [
        '/ventas/carrito',
        '/ventas/carrito/items/8',
        '/ventas/carrito/items/8',
        '/ventas/carrito/confirmar',
        '/pagos',
      ]);
      expect(api.requests[0]['data'], {'sucursal_id': 3});
      expect(api.requests[1]['data'], {'cantidad': 2});
      expect(api.requests[2]['data'], isNull);
      expect(api.requests[4]['data'], {
        'venta_id': 4,
        'metodo': 'tarjeta',
        'monto': 80.0,
        'numero_tarjeta': '4242424242424242',
      });
      expect(api.requests[4]['data'].toString(), contains('4242'));
      expect(
        api.requests[4]['data'].toString(),
        isNot(contains('simular_fallo')),
      );
      expect(
        api.requests[4]['data'].toString().toLowerCase(),
        isNot(contains('cvc')),
      );
    },
  );

  test(
    'discovers mobile methods and preserves availability metadata',
    () async {
      final api = _FakeApi();
      final methods = await CartService(api).fetchPaymentMethods();

      expect(api.requests.last, {
        'path': '/pagos/metodos',
        'method': 'GET',
        'data': null,
        'queryParameters': const {'canal': 'movil'},
      });
      expect(methods.map((method) => method.value), ['tarjeta', 'qr']);
      expect(methods.first.available, isTrue);
      expect(methods.first.gateway, 'stripe');
      expect(methods.first.mode, 'simulado');
      expect(methods.last.available, isFalse);
      expect(methods.last.detail, contains('BCP'));
    },
  );

  test('creates and polls a QR through the live mobile contracts', () async {
    final api = _FakeApi();
    final service = CartService(api);

    final created = await service.createQr(saleId: 4);
    final polled = await service.pollQr(saleId: 4, qrId: created.qrId);

    expect(api.requests[0]['path'], '/pagos/qr');
    expect(api.requests[0]['data'], {'venta_id': 4});
    expect(api.requests[1]['path'], '/pagos/qr/qr-4');
    expect(api.requests[1]['queryParameters'], {'venta_id': 4});
    expect(created.state, QrPaymentState.pending);
    expect(polled.state, QrPaymentState.approved);
    expect(polled.paymentResult?.paymentLabel, 'QR (BCP)');
  });

  test('maps a missing cart response to null', () async {
    final service = CartService(_FakeApi(absentCart: true));
    expect(await service.fetchCart(), isNull);
  });

  test(
    'maps backend cart prices and delivery summary without recalculation',
    () async {
      final cart = await CartService(_FakeApi()).fetchCart();

      expect(cart?.subtotal, 91.25);
      expect(cart?.discount, 8.75);
      expect(cart?.shippingCost, 6.5);
      expect(cart?.total, 89.0);
      expect(cart?.deliveryType, 'delivery');
      expect(cart?.shipment?.address, 'Calle 10 #45');
      expect(cart?.lines.single.unitPrice, 50.0);
      expect(cart?.lines.single.finalPrice, 41.25);
      expect(cart?.lines.single.discount, 8.75);
      expect(cart?.lines.single.promotion?.displayName, 'Oferta web');
    },
  );
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
    requests.add({
      'path': path,
      'method': method,
      'data': data,
      'queryParameters': queryParameters,
    });
    final response = switch (path) {
      '/pagos/metodos' => {
        'canal': 'movil',
        'metodos': [
          {
            'valor': 'tarjeta',
            'etiqueta': 'Tarjeta',
            'disponible': true,
            'pasarela': 'stripe',
            'detalle': 'Stripe listo',
            'modo': 'simulado',
          },
          {
            'valor': 'qr',
            'etiqueta': 'QR BCP',
            'disponible': false,
            'pasarela': 'bcp_qr',
            'detalle': 'BCP no configurado',
            'modo': 'sandbox',
          },
        ],
      },
      '/pagos/qr' => {
        'venta_id': 4,
        'pago_id': 8,
        'qr_id': 'qr-4',
        'estado': 'C',
        'descripcion': 'EN COLA',
        'imagen_base64': 'cWk=',
        'monto': 80,
        'moneda': 'BOB',
      },
      '/pagos/qr/qr-4' => {
        'venta_id': 4,
        'pago_id': 8,
        'qr_id': 'qr-4',
        'estado': 'P',
        'aprobado': true,
        'nro_comprobante': 'C-000001',
        'pago': {
          'referencia_externa': 'qr-4',
          'etiqueta': 'QR (BCP)',
          'pasarela': 'bcp_qr',
        },
        'venta': _sale('pagada'),
      },
      '/pagos' => {
        'aprobado': true,
        'nro_comprobante': 'C-000001',
        'pago': {'referencia_externa': 'pi_test_1'},
        'venta': _sale('pagada'),
      },
      _ => _sale('carrito'),
    };
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
      statusCode: 200,
    );
  }
}

Map<String, dynamic> _sale(String status) => {
  'id': 4,
  'estado': status,
  'sucursal_id': 2,
  'sucursal': 'Centro',
  'unidades': 1,
  'subtotal': 91.25,
  'descuento': 8.75,
  'tipo_entrega': 'delivery',
  'costo_envio': 6.5,
  'envio': {'direccion': 'Calle 10 #45'},
  'total': 89,
  'detalle': [
    {
      'id': 8,
      'variante_id': 9,
      'sku': 'GC-09',
      'prenda': 'Camisa',
      'talla': 'M',
      'color': 'Azul',
      'cantidad': 1,
      'precio_unitario': 50,
      'precio_final': 41.25,
      'descuento': 8.75,
      'promocion': {'id': 2, 'nombre': 'Oferta', 'etiqueta': 'Oferta web'},
      'subtotal': 41.25,
    },
  ],
};
