import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/core/storage/preferences_storage.dart';
import 'package:mobile/features/ai/ai_controller.dart';
import 'package:mobile/features/ai/ai_models.dart';
import 'package:mobile/features/ai/ai_service.dart';

void main() {
  test('forwards the selected branch to chat', () async {
    final api = _FakeAiApi();
    final controller = AiController(api: api, preferences: _Preferences(8));

    await controller.load();
    await controller.sendMessage('hola');

    expect(api.chatBranch, 8);
    expect(api.chatOriginIsMobile, isTrue);
    expect(controller.messages.last.text, 'Respuesta respaldada');
  });

  test('keeps sin_modelo and exposes empty and unauthorized states', () async {
    final controller = AiController(
      api: _FakeAiApi(unauthorizedRecommendations: true),
      preferences: _Preferences(null),
    );

    await controller.load();
    await controller.loadRecommendations();

    expect(controller.status?.model.mode, 'sin_modelo');
    expect(controller.recommendations, isNull);
    expect(controller.unauthorized, isTrue);
  });

  test('conversation CRUD updates local state after backend calls', () async {
    final api = _FakeAiApi();
    final controller = AiController(api: api, preferences: _Preferences(null));

    await controller.loadConversations();
    await controller.openConversationById(3);
    await controller.deleteConversationById(3);

    expect(api.openedConversation, 3);
    expect(api.deletedConversation, 3);
    expect(controller.conversations, isEmpty);
    expect(controller.messages, isEmpty);
  });

  test(
    'clearConversation clears local state even if server delete fails',
    () async {
      final api = _FakeAiApi()..deleteFails = true;
      final controller = AiController(
        api: api,
        preferences: _Preferences(null),
      );
      controller
        ..conversationId = 3
        ..conversationTitle = 'Consulta'
        ..messages = const [AiChatMessage(role: 'usuario', text: 'Hola')];

      await controller.clearConversation();

      expect(controller.conversationId, isNull);
      expect(controller.messages, isEmpty);
      expect(controller.conversations, isEmpty);
    },
  );
}

class _Preferences implements BranchPreferenceStore {
  _Preferences(this.branch);

  final int? branch;

  @override
  Future<int?> readSelectedBranch() async => branch;

  @override
  Future<void> saveSelectedBranch(int? branchId) async {}
}

class _FakeAiApi implements AiDataSource {
  _FakeAiApi({this.unauthorizedRecommendations = false});

  final bool unauthorizedRecommendations;
  int? recommendationBranch;
  int? chatBranch;
  bool chatOriginIsMobile = false;
  int? openedConversation;
  int? deletedConversation;
  bool deleteFails = false;

  @override
  Future<AiStatus> fetchStatus() async => AiStatus.withoutModel;

  @override
  Future<AiRecommendations> fetchRecommendations({
    required int limit,
    int? branchId,
  }) async {
    recommendationBranch = branchId;
    if (unauthorizedRecommendations) {
      throw const ApiError(statusCode: 401, message: 'No autorizado');
    }
    return const AiRecommendations();
  }

  @override
  Future<void> sendEvent({
    required int productId,
    required String eventType,
  }) async {}

  @override
  Future<AiChatResponse> sendChat({
    required String message,
    int? conversationId,
    int? branchId,
  }) async {
    chatBranch = branchId;
    chatOriginIsMobile = true;
    return const AiChatResponse(response: 'Respuesta respaldada');
  }

  @override
  Future<List<AiConversationSummary>> fetchConversations() async => const [
    AiConversationSummary(id: 3, title: 'Consulta'),
  ];

  @override
  Future<AiConversationDetail> fetchConversation(int id) async {
    openedConversation = id;
    return const AiConversationDetail(
      id: 3,
      title: 'Consulta',
      messages: [AiChatMessage(role: 'assistant', text: 'Hola')],
    );
  }

  @override
  Future<void> deleteConversation(int id) async {
    deletedConversation = id;
    if (deleteFails) throw StateError('offline');
  }
}
