import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/ai/ai_models.dart';
import 'package:mobile/features/ai/ai_service.dart';

void main() {
  test(
    'uses exact AI paths, query parameters, and request contracts',
    () async {
      final api = _FakeApi();
      final service = AiService(api);

      await service.fetchStatus();
      await service.fetchRecommendations(limit: 1, branchId: 8);
      await service.sendEvent(productId: 12, eventType: 'vista');
      await service.sendChat(
        message: 'busco una camisa',
        conversationId: 4,
        branchId: 8,
      );
      await service.fetchConversations();
      await service.fetchConversation(4);
      await service.deleteConversation(4);

      expect(api.calls.map((call) => call.path), [
        '/ia/estado',
        '/ia/recomendaciones',
        '/ia/eventos',
        '/ia/chat',
        '/ia/conversaciones',
        '/ia/conversaciones/4',
        '/ia/conversaciones/4',
      ]);
      expect(api.calls[1].query, {'limite': 1, 'sucursal_id': 8});
      expect(api.calls[2].data, {
        'prenda_id': 12,
        'tipo_evento': 'vista',
        'origen': 'movil',
      });
      expect(api.calls[3].data, {
        'mensaje': 'busco una camisa',
        'conversacion_id': 4,
        'origen': 'movil',
        'sucursal_id': 8,
      });
      expect(api.calls[6].method, 'DELETE');
    },
  );

  test('parses backend recommendation values without recalculating them', () {
    final status = AiStatus.fromJson({
      'modelo': {
        'modo': 'sin_modelo',
        'disponible': false,
        'motivo': 'offline',
      },
      'recomendador': {'disponible': false},
    });
    final item = AiRecommendationItem.fromJson({
      'id': 12,
      'nombre': 'Camisa',
      'precio_venta': 100,
      'precio_final': 81.25,
      'descuento': 2.5,
      'promocion': {'nombre': 'Oferta', 'valor': 40},
      'disponible_total': 3,
      'puntaje': 0.82,
    });

    expect(status.model.isWithoutModel, isTrue);
    expect(status.model.reason, 'offline');
    expect(item.salePrice, 100);
    expect(item.finalPrice, 81.25);
    expect(item.discount, 2.5);
    expect(item.stock, 3);
    expect(item.promotion?.value, 40);
    expect(AiStatus.fromJson({}).model.mode, 'sin_modelo');
  });

  test('rejects recommendation limits outside the backend contract', () async {
    final service = AiService(_FakeApi());
    expect(() => service.fetchRecommendations(limit: 0), throwsArgumentError);
    expect(() => service.fetchRecommendations(limit: 21), throwsArgumentError);
  });

  test(
    'best-effort event delivery never throws into the customer flow',
    () async {
      final sink = BestEffortAiEventSink(_ThrowingEventSink());
      await expectLater(
        sink.reportProductEvent(productId: 12, eventType: 'carrito'),
        completes,
      );
    },
  );
}

class _ThrowingEventSink implements AiEventSink {
  @override
  Future<void> reportProductEvent({
    required int productId,
    required String eventType,
  }) async {
    throw StateError('analytics offline');
  }
}

class _Call {
  _Call(this.path, this.method, this.data, this.query);

  final String path;
  final String method;
  final Object? data;
  final Map<String, dynamic> query;
}

class _FakeApi extends ApiClient {
  _FakeApi() : super(dio: Dio());

  final calls = <_Call>[];

  @override
  Future<Response<T>> request<T>(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    calls.add(_Call(path, method, data, queryParameters ?? const {}));
    final response = switch (path) {
      '/ia/estado' => {
        'modelo': {'modo': 'sin_modelo', 'disponible': false},
        'recomendador': {'disponible': false},
      },
      '/ia/recomendaciones' => {'items': <Object?>[]},
      '/ia/chat' => {'respuesta': 'ok'},
      '/ia/conversaciones' => <Object?>[],
      '/ia/conversaciones/4' => {
        'id': 4,
        'titulo': 'Prueba',
        'mensajes': <Object?>[],
      },
      _ => <String, dynamic>{},
    };
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
      statusCode: 200,
    );
  }
}
