import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../core/storage/preferences_storage.dart';
import '../../features/auth/session_model.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_loading_empty_error.dart';
import 'ai_controller.dart';
import 'ai_models.dart';
import 'ai_service.dart';

class AiScreen extends StatefulWidget {
  const AiScreen({
    this.apiClient,
    this.preferencesStorage,
    required this.session,
    this.controller,
    super.key,
  });

  final ApiClient? apiClient;
  final PreferencesStorage? preferencesStorage;
  final Session? session;
  final AiController? controller;

  @override
  State<AiScreen> createState() => _AiScreenState();
}

class _AiScreenState extends State<AiScreen> {
  static const _suggestions = [
    '¿Qué me recomendás?',
    '¿Hay promociones?',
    'Busco algo para una fiesta',
  ];

  late final AiController _controller;
  late final TextEditingController _messageController;

  @override
  void initState() {
    super.initState();
    _controller =
        widget.controller ??
        AiController(
          api: AiService(
            widget.apiClient ??
                (throw StateError('AI modal requires an ApiClient')),
          ),
          preferences: widget.preferencesStorage,
        );
    _messageController = TextEditingController();
    _controller.addListener(_onChanged);
    _controller.load();
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _controller.removeListener(_onChanged);
    if (widget.controller == null) _controller.dispose();
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final height = (MediaQuery.sizeOf(context).height * 0.86)
        .clamp(420.0, 680.0)
        .toDouble();
    return SizedBox(
      height: height,
      child: Material(
        color: GangaColors.paper,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            _buildHeader(),
            Expanded(child: _buildConversation()),
            _buildComposer(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() => Container(
    padding: const EdgeInsets.fromLTRB(16, 13, 8, 12),
    decoration: const BoxDecoration(
      color: GangaColors.white,
      border: Border(bottom: BorderSide(color: GangaColors.line)),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Asistente de compras', style: GangaTextStyles.subheading),
              SizedBox(height: 3),
              Text(
                'Preguntame qué buscás y te ayudo.',
                style: TextStyle(color: GangaColors.gray, fontSize: 12),
              ),
            ],
          ),
        ),
        if (_hasActiveConversation)
          IconButton(
            tooltip: 'Vaciar la conversación',
            onPressed: () => _controller.clearConversation(),
            icon: const Icon(Icons.delete_outline),
          ),
        IconButton(
          tooltip: 'Cerrar',
          onPressed: () => Navigator.of(context).pop(),
          icon: const Icon(Icons.close),
        ),
      ],
    ),
  );

  Widget _buildConversation() {
    final status = _controller.status;
    return ListView(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 18),
      children: [
        if (status == null && _controller.loading)
          const GcLoadingEmptyError(state: GcPanelState.loading)
        else if (status == null)
          GcLoadingEmptyError(
            state: GcPanelState.error,
            errorTitle: 'No se pudo consultar el asistente',
            errorMessage: _controller.error?.message ?? 'Intenta de nuevo.',
            retryLabel: 'Reintentar',
            onRetry: _controller.load,
          )
        else if (_controller.unauthorized)
          const GcLoadingEmptyError(
            state: GcPanelState.error,
            errorTitle: 'Iniciá sesión para usar el asistente',
            errorMessage: 'Las conversaciones son privadas.',
          )
        else ...[
          _buildStatus(status),
          const SizedBox(height: 14),
          if (_controller.messages.isEmpty) _buildWelcome(),
          ..._controller.messages.map(_buildMessage),
          if (_controller.chatLoading)
            const Padding(
              padding: EdgeInsets.only(top: 4),
              child: Text(
                'Pensando…',
                style: TextStyle(color: GangaColors.gray, fontSize: 12),
              ),
            ),
          if (_controller.chatError != null) ...[
            const SizedBox(height: 8),
            GcFeedback(
              message: _controller.chatError!.message,
              variant: GcFeedbackVariant.error,
            ),
          ],
        ],
      ],
    );
  }

  Widget _buildStatus(AiStatus status) {
    if (status.model.isWithoutModel) {
      return const GcFeedback(
        message:
            'El asistente está disponible en modo sin_modelo. No se mostrarán afirmaciones que no vengan del backend.',
      );
    }
    return GcFeedback(
      message: status.model.model == null
          ? 'Asistente disponible.'
          : 'Asistente disponible · ${status.model.model}',
      variant: GcFeedbackVariant.success,
    );
  }

  Widget _buildWelcome() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const Text(
        'Puedo buscarte prendas, contarte las promociones y ayudarte según lo que ya compraste.',
        style: TextStyle(color: GangaColors.gray, fontSize: 13, height: 1.45),
      ),
      const SizedBox(height: 12),
      Wrap(
        spacing: 7,
        runSpacing: 7,
        children: [
          for (final suggestion in _suggestions)
            ActionChip(
              label: Text(suggestion),
              onPressed: _controller.chatLoading
                  ? null
                  : () => _controller.sendMessage(suggestion),
            ),
        ],
      ),
    ],
  );

  Widget _buildMessage(AiChatMessage message) => Align(
    alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
    child: Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      constraints: const BoxConstraints(maxWidth: 340),
      decoration: BoxDecoration(
        color: message.isUser ? GangaColors.brand : GangaColors.white,
        border: Border.all(
          color: message.isUser ? GangaColors.brand : GangaColors.line,
        ),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        message.text,
        style: TextStyle(color: message.isUser ? GangaColors.white : null),
      ),
    ),
  );

  Widget _buildComposer() => Container(
    padding: const EdgeInsets.fromLTRB(12, 9, 12, 10),
    decoration: const BoxDecoration(
      color: GangaColors.white,
      border: Border(top: BorderSide(color: GangaColors.line)),
    ),
    child: Column(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                minLines: 1,
                maxLines: 4,
                enabled: !_controller.chatLoading && !_controller.unauthorized,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => _sendMessage(),
                decoration: const InputDecoration(
                  labelText: 'Escribí tu mensaje…',
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              tooltip: 'Enviar mensaje',
              onPressed: _controller.chatLoading || _controller.unauthorized
                  ? null
                  : _sendMessage,
              icon: _controller.chatLoading
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send),
            ),
          ],
        ),
        const SizedBox(height: 4),
        const Align(
          alignment: Alignment.centerLeft,
          child: Text(
            'Solo informa con datos respaldados por el backend. No realiza compras ni reservas.',
            style: TextStyle(color: GangaColors.gray, fontSize: 11),
          ),
        ),
      ],
    ),
  );

  bool get _hasActiveConversation =>
      _controller.conversationId != null || _controller.messages.isNotEmpty;

  void _sendMessage() {
    final value = _messageController.text;
    if (value.trim().isEmpty) return;
    _messageController.clear();
    _controller.sendMessage(value);
  }
}
