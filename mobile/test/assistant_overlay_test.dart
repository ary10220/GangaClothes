import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/storage/preferences_storage.dart';
import 'package:mobile/features/ai/ai_controller.dart';
import 'package:mobile/features/ai/ai_models.dart';
import 'package:mobile/features/ai/ai_service.dart';
import 'package:mobile/features/ai/assistant_modal_overlay.dart';
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

  testWidgets('opens the chatbot as a modal and closes without a route', (
    tester,
  ) async {
    final preferences = await _preferences();
    final controller = AiController(
      api: _OverlayApi(),
      preferences: preferences,
    );
    await tester.pumpWidget(
      MaterialApp(
        home: AssistantModalOverlay(
          session: session,
          controller: controller,
          child: const Scaffold(body: Text('Catalog route')),
        ),
      ),
    );

    await tester.tap(find.byTooltip('Abrir asistente'));
    await tester.pumpAndSettle();

    expect(find.text('Catalog route'), findsOneWidget);
    expect(find.text('Asistente de compras'), findsOneWidget);
    expect(find.text('Recomendaciones para vos'), findsNothing);
    expect(find.byTooltip('Cerrar'), findsOneWidget);

    await tester.tap(find.byTooltip('Cerrar'));
    await tester.pumpAndSettle();
    expect(find.text('Asistente de compras'), findsNothing);
    expect(find.text('Catalog route'), findsOneWidget);
  });

  testWidgets('guests keep the floating entry but are sent to login', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        routes: {'login': (_) => const Scaffold(body: Text('Login route'))},
        home: const AssistantModalOverlay(
          child: Scaffold(body: Text('Catalog route')),
        ),
      ),
    );

    await tester.tap(find.byTooltip('Abrir asistente'));
    await tester.pumpAndSettle();

    expect(find.text('Login route'), findsOneWidget);
    expect(find.text('Asistente de compras'), findsNothing);
  });

  testWidgets('does not render the assistant button on auth screens', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AssistantModalOverlay(
          showAssistant: false,
          child: Scaffold(body: Text('Authentication route')),
        ),
      ),
    );

    expect(find.byTooltip('Abrir asistente'), findsNothing);
  });
}

Future<PreferencesStorage> _preferences() async {
  SharedPreferences.setMockInitialValues({});
  return PreferencesStorage.fromInstance(await SharedPreferences.getInstance());
}

class _OverlayApi implements AiDataSource {
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
  }) async => const AiChatResponse(response: 'Respuesta textual');

  @override
  Future<List<AiConversationSummary>> fetchConversations() async => const [];

  @override
  Future<AiConversationDetail> fetchConversation(int id) async =>
      const AiConversationDetail(id: 1, title: 'Consulta');

  @override
  Future<void> deleteConversation(int id) async {}
}
