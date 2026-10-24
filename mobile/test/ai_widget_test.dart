import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/storage/preferences_storage.dart';
import 'package:mobile/features/ai/ai_controller.dart';
import 'package:mobile/features/ai/ai_models.dart';
import 'package:mobile/features/ai/ai_screen.dart';
import 'package:mobile/features/ai/ai_service.dart';
import 'package:mobile/features/auth/session_model.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  const session = Session(
    accessToken: 'token',
    user: User(
      id: 1,
      name: 'Cliente',
      email: 'cliente@example.com',
      roles: ['cliente'],
    ),
  );

  testWidgets('shows the textual chatbot without recommendation UI', (
    tester,
  ) async {
    final preferences = await _preferences();
    await tester.pumpWidget(
      MaterialApp(
        home: AiScreen(
          apiClient: ApiClient(dio: Dio()),
          preferencesStorage: preferences,
          session: session,
          controller: AiController(api: _WidgetApi(), preferences: preferences),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('sin_modelo'), findsOneWidget);
    expect(find.text('Recomendaciones para vos'), findsNothing);
    expect(find.text('PARA VOS'), findsNothing);
    expect(find.text('CONVERSACIONES'), findsNothing);
    expect(find.text('¿Qué me recomendás?'), findsOneWidget);
  });
}

Future<PreferencesStorage> _preferences() async {
  SharedPreferences.setMockInitialValues({});
  return PreferencesStorage.fromInstance(await SharedPreferences.getInstance());
}

class _WidgetApi implements AiDataSource {
  @override
  Future<AiStatus> fetchStatus() async => AiStatus.withoutModel;

  @override
  Future<AiRecommendations> fetchRecommendations({
    required int limit,
    int? branchId,
  }) async => const AiRecommendations();

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
  }) async => const AiChatResponse(response: 'ok');

  @override
  Future<List<AiConversationSummary>> fetchConversations() async => const [];

  @override
  Future<AiConversationDetail> fetchConversation(int id) async =>
      const AiConversationDetail(id: 1, title: 'Consulta');

  @override
  Future<void> deleteConversation(int id) async {}
}
