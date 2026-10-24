import '../../core/network/api_client.dart';
import 'ai_models.dart';

abstract interface class AiDataSource {
  Future<AiStatus> fetchStatus();

  Future<AiRecommendations> fetchRecommendations({
    required int limit,
    int? branchId,
  });

  Future<void> sendEvent({required int productId, required String eventType});

  Future<AiChatResponse> sendChat({
    required String message,
    int? conversationId,
    int? branchId,
  });

  Future<List<AiConversationSummary>> fetchConversations();

  Future<AiConversationDetail> fetchConversation(int id);

  Future<void> deleteConversation(int id);
}

abstract interface class AiEventSink {
  Future<void> reportProductEvent({
    required int productId,
    required String eventType,
  });
}

class AiService implements AiDataSource, AiEventSink {
  const AiService(this.apiClient);

  final ApiClient apiClient;

  @override
  Future<AiStatus> fetchStatus() async {
    final response = await apiClient.request<Object?>('/ia/estado');
    return AiStatus.fromJson(_map(response.data));
  }

  @override
  Future<AiRecommendations> fetchRecommendations({
    required int limit,
    int? branchId,
  }) async {
    if (limit < 1 || limit > 20) {
      throw ArgumentError.value(limit, 'limit', 'must be between 1 and 20');
    }
    final response = await apiClient.request<Object?>(
      '/ia/recomendaciones',
      queryParameters: {
        'limite': limit,
        ...?(branchId == null ? null : {'sucursal_id': branchId}),
      },
    );
    return AiRecommendations.fromJson(response.data);
  }

  @override
  Future<void> sendEvent({required int productId, required String eventType}) =>
      reportProductEvent(productId: productId, eventType: eventType);

  @override
  Future<void> reportProductEvent({
    required int productId,
    required String eventType,
  }) async {
    await apiClient.request<Object?>(
      '/ia/eventos',
      method: 'POST',
      data: {
        'prenda_id': productId,
        'tipo_evento': eventType,
        'origen': 'movil',
      },
    );
  }

  @override
  Future<AiChatResponse> sendChat({
    required String message,
    int? conversationId,
    int? branchId,
  }) async {
    final response = await apiClient.request<Object?>(
      '/ia/chat',
      method: 'POST',
      data: {
        'mensaje': message,
        ...?(conversationId == null
            ? null
            : {'conversacion_id': conversationId}),
        'origen': 'movil',
        ...?(branchId == null ? null : {'sucursal_id': branchId}),
      },
    );
    return AiChatResponse.fromJson(_map(response.data));
  }

  @override
  Future<List<AiConversationSummary>> fetchConversations() async {
    final response = await apiClient.request<Object?>('/ia/conversaciones');
    return _maps(
      response.data,
      key: 'conversaciones',
    ).map(AiConversationSummary.fromJson).toList(growable: false);
  }

  @override
  Future<AiConversationDetail> fetchConversation(int id) async {
    final response = await apiClient.request<Object?>('/ia/conversaciones/$id');
    return AiConversationDetail.fromJson(_map(response.data));
  }

  @override
  Future<void> deleteConversation(int id) async {
    await apiClient.request<Object?>(
      '/ia/conversaciones/$id',
      method: 'DELETE',
    );
  }
}

class BestEffortAiEventSink implements AiEventSink {
  const BestEffortAiEventSink(this.delegate);

  final AiEventSink delegate;

  @override
  Future<void> reportProductEvent({
    required int productId,
    required String eventType,
  }) async {
    try {
      await delegate.reportProductEvent(
        productId: productId,
        eventType: eventType,
      );
    } catch (_) {
      // Analytics must never block catalog, cart, or checkout actions.
    }
  }
}

Map<String, dynamic> _map(Object? value) {
  if (value is! Map) throw const FormatException('Expected a JSON object');
  return Map<String, dynamic>.from(value);
}

List<Map<String, dynamic>> _maps(Object? value, {String? key}) {
  final source = value is Map && key != null ? value[key] : value;
  if (source is! Iterable) return const [];
  return source
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList(growable: false);
}
