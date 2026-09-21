import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import '../../core/storage/preferences_storage.dart';
import 'ai_models.dart';
import 'ai_service.dart';

class AiController extends ChangeNotifier {
  AiController({required this.api, this.preferences});

  final AiDataSource api;
  final BranchPreferenceStore? preferences;

  AiStatus? status;
  AiRecommendations? recommendations;
  List<AiConversationSummary> conversations = const [];
  AiConversationDetail? openConversation;
  List<AiChatMessage> messages = const [];
  ApiError? error;
  ApiError? chatError;
  bool loading = false;
  bool recommendationsLoading = false;
  bool conversationsLoading = false;
  bool chatLoading = false;
  bool unauthorized = false;
  int? selectedBranchId;
  int? conversationId;
  String? conversationTitle;
  bool _disposed = false;

  Future<void> load() async {
    loading = true;
    error = null;
    unauthorized = false;
    _notify();
    selectedBranchId = await _readBranch();
    try {
      status = await api.fetchStatus();
    } catch (caught) {
      error = _asApiError(caught);
      if (error!.statusCode == 401) unauthorized = true;
    }
    loading = false;
    _notify();
  }

  Future<void> loadRecommendations() async {
    recommendationsLoading = true;
    _notify();
    try {
      recommendations = await api.fetchRecommendations(
        limit: 6,
        branchId: selectedBranchId,
      );
    } catch (caught) {
      final normalized = _asApiError(caught);
      if (normalized.statusCode == 401) unauthorized = true;
      error ??= normalized;
    } finally {
      recommendationsLoading = false;
      _notify();
    }
  }

  Future<void> sendMessage(String value) async {
    final message = value.trim();
    if (message.isEmpty || chatLoading) return;
    chatLoading = true;
    chatError = null;
    messages = [...messages, AiChatMessage(role: 'usuario', text: message)];
    _notify();
    try {
      final result = await api.sendChat(
        message: message,
        conversationId: conversationId,
        branchId: selectedBranchId,
      );
      conversationId = result.conversationId ?? conversationId;
      conversationTitle = result.title ?? conversationTitle;
      messages = [
        ...messages,
        AiChatMessage(role: 'assistant', text: result.response),
      ];
    } catch (caught) {
      final normalized = _asApiError(caught);
      if (normalized.statusCode == 401) unauthorized = true;
      chatError = normalized;
    } finally {
      chatLoading = false;
      _notify();
    }
  }

  Future<void> loadConversations() async {
    conversationsLoading = true;
    _notify();
    try {
      conversations = await api.fetchConversations();
    } catch (caught) {
      final normalized = _asApiError(caught);
      if (normalized.statusCode == 401) unauthorized = true;
      error ??= normalized;
    } finally {
      conversationsLoading = false;
      _notify();
    }
  }

  Future<void> openConversationById(int id) async {
    try {
      final detail = await api.fetchConversation(id);
      openConversation = detail;
      conversationId = detail.id;
      conversationTitle = detail.title;
      messages = detail.messages;
      _notify();
    } catch (caught) {
      final normalized = _asApiError(caught);
      if (normalized.statusCode == 401) unauthorized = true;
      error = normalized;
      _notify();
    }
  }

  Future<void> deleteConversationById(int id) async {
    try {
      await api.deleteConversation(id);
      conversations = conversations
          .where((item) => item.id != id)
          .toList(growable: false);
      if (conversationId == id) {
        conversationId = null;
        conversationTitle = null;
        openConversation = null;
        messages = const [];
      }
      _notify();
    } catch (caught) {
      error = _asApiError(caught);
      _notify();
    }
  }

  /// Clears the active chat immediately and best-effort clears its server copy.
  /// A failed delete must not block the user from starting a new conversation.
  Future<void> clearConversation() async {
    final id = conversationId;
    conversations = id == null
        ? conversations
        : conversations.where((item) => item.id != id).toList(growable: false);
    conversationId = null;
    conversationTitle = null;
    openConversation = null;
    messages = const [];
    chatError = null;
    _notify();

    if (id == null) return;
    try {
      await api.deleteConversation(id);
    } catch (_) {
      // Local chat state is intentionally cleared even when the server is down.
    }
  }

  Future<int?> _readBranch() async {
    try {
      return await preferences?.readSelectedBranch();
    } catch (_) {
      return null;
    }
  }

  static ApiError _asApiError(Object caught) => caught is ApiError
      ? caught
      : ApiError(statusCode: 0, message: '$caught', cause: caught);

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
