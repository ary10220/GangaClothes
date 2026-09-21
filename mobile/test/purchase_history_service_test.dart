import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_error.dart';
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

  test('fetches the authenticated JSON receipt', () async {
    final api = _FakePurchaseApi(receiptData: _receipt());

    final receipt = await PurchaseHistoryService(api).fetchReceipt(7);

    expect(receipt.receiptNumber, 'FAC-7');
    expect(receipt.total, 91);
    expect(api.path, '/ventas/7/comprobante');
    expect(api.method, 'GET');
  });

  test('propagates a JSON receipt error for the controller boundary', () async {
    final api = _FakePurchaseApi(receiptFailure: true);

    expect(
      () => PurchaseHistoryService(api).fetchReceipt(7),
      throwsA(isA<ApiError>()),
    );
  });

  test('fetches authenticated PDF bytes with a byte response type', () async {
    final api = _FakePurchaseApi(pdfData: Uint8List.fromList([37, 80, 68, 70]));

    final bytes = await PurchaseHistoryService(api).fetchReceiptPdf(7);

    expect(bytes, orderedEquals([37, 80, 68, 70]));
    expect(api.path, '/ventas/7/comprobante.pdf');
    expect(api.method, 'GET');
    expect(api.responseType, ResponseType.bytes);
  });
}

class _FakePurchaseApi extends ApiClient {
  _FakePurchaseApi({
    this.data,
    this.receiptData,
    this.pdfData,
    this.receiptFailure = false,
  }) : super(dio: Dio());

  final Object? data;
  final Object? receiptData;
  final Uint8List? pdfData;
  final bool receiptFailure;
  String? path;
  String? method;
  ResponseType? responseType;

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
    responseType = options?.responseType;
    if (requestPath.endsWith('.pdf')) {
      return Response<T>(
        requestOptions: RequestOptions(path: requestPath),
        data: (pdfData ?? Uint8List.fromList(const [37, 80, 68, 70])) as T,
        statusCode: 200,
      );
    }
    if (requestPath.contains('/comprobante')) {
      if (receiptFailure) {
        throw const ApiError(statusCode: 503, message: 'Receipt unavailable');
      }
      return Response<T>(
        requestOptions: RequestOptions(path: requestPath),
        data: (receiptData ?? <String, dynamic>{}) as T,
        statusCode: 200,
      );
    }
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

Map<String, dynamic> _receipt() => {
  'nro_comprobante': 'FAC-7',
  'fecha': '2030-04-05T09:07:06Z',
  'items': <Object?>[],
  'subtotal': 100,
  'descuento': 10,
  'costo_envio': 1,
  'entrega': {'tipo_entrega': 'delivery'},
  'total': 91,
  'moneda': 'BOB',
  'pago': {
    'metodo': 'tarjeta',
    'monto': 91,
    'estado': 'exitoso',
    'referencia_externa': 'pay-7',
  },
};
