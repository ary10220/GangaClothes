import 'package:flutter/material.dart';

import '../../core/network/api_client.dart';
import '../../core/storage/preferences_storage.dart';
import '../../features/auth/session_model.dart';
import 'ai_controller.dart';
import 'ai_screen.dart';

class AssistantModalOverlay extends StatelessWidget {
  const AssistantModalOverlay({
    required this.child,
    this.apiClient,
    this.preferencesStorage,
    this.session,
    this.controller,
    this.loginRoute = 'login',
    this.loginArguments,
    this.showAssistant = true,
    super.key,
  });

  final Widget child;
  final ApiClient? apiClient;
  final PreferencesStorage? preferencesStorage;
  final Session? session;
  final AiController? controller;
  final String loginRoute;
  final Object? loginArguments;
  final bool showAssistant;

  @override
  Widget build(BuildContext context) => Stack(
    fit: StackFit.expand,
    children: [
      child,
      if (showAssistant)
        Positioned.fill(
          child: Align(
            alignment: Alignment.bottomRight,
            child: SafeArea(
              minimum: const EdgeInsets.only(right: 16, bottom: 16),
              child: Semantics(
                button: true,
                label: 'Abrir asistente',
                child: FloatingActionButton(
                  heroTag: null,
                  tooltip: 'Abrir asistente',
                  onPressed: () => _openAssistant(context),
                  child: const Icon(
                    Icons.chat_bubble_outline,
                    semanticLabel: 'Abrir asistente',
                  ),
                ),
              ),
            ),
          ),
        ),
    ],
  );

  void _openAssistant(BuildContext context) {
    if (session == null) {
      Navigator.of(context).pushNamed(loginRoute, arguments: loginArguments);
      return;
    }

    final api = apiClient;
    final preferences = preferencesStorage;
    if (controller == null && (api == null || preferences == null)) {
      return;
    }

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (_) => AiScreen(
        apiClient: api,
        preferencesStorage: preferences,
        session: session,
        controller: controller,
      ),
    );
  }
}
