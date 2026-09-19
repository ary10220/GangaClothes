import 'package:dio/dio.dart';

class ApiError implements Exception {
  const ApiError({
    required this.statusCode,
    required this.message,
    this.details,
    this.cause,
  });

  final int statusCode;
  final String message;
  final Object? details;
  final Object? cause;

  bool get isNetworkError => statusCode == 0;

  factory ApiError.fromDioException(DioException error) {
    final statusCode = error.response?.statusCode ?? 0;
    return ApiError(
      statusCode: statusCode,
      message: _messageFor(statusCode, error.response?.data),
      details: error.response?.data,
      cause: error,
    );
  }

  factory ApiError.fromStatus(
    int statusCode,
    Object? data, {
    String? fallbackMessage,
  }) {
    return ApiError(
      statusCode: statusCode,
      message: _messageFor(statusCode, data, fallbackMessage: fallbackMessage),
      details: data,
    );
  }

  @override
  String toString() => 'ApiError($statusCode): $message';
}

String _messageFor(int statusCode, Object? data, {String? fallbackMessage}) {
  final detail = _detailText(data);
  if (detail != null) return detail;
  if (fallbackMessage != null && fallbackMessage.trim().isNotEmpty) {
    return fallbackMessage;
  }

  switch (statusCode) {
    case 0:
      return 'No se pudo contactar al servidor.';
    case 401:
      return 'Tu sesión expiró o no es válida.';
    case 402:
      return 'El pago fue rechazado.';
    case 403:
      return 'No tienes permisos para realizar esta operación.';
    default:
      if (statusCode >= 500) {
        return 'Error interno del servidor. Intenta de nuevo en un momento.';
      }
      return 'La solicitud no pudo completarse.';
  }
}

String? _detailText(Object? data) {
  if (data is String && data.trim().isNotEmpty) return data;
  if (data is! Map) return null;

  final detail = data['detail'];
  if (detail is String && detail.trim().isNotEmpty) return detail;
  if (detail is Iterable) {
    final messages = detail.map(_validationItem).whereType<String>().toList();
    if (messages.isNotEmpty) return messages.join(' · ');
  }
  return null;
}

String? _validationItem(Object? item) {
  if (item is! Map) return null;
  final message = item['msg'];
  if (message is! String || message.trim().isEmpty) return null;
  final location = item['loc'];
  if (location is Iterable && location.isNotEmpty) {
    return '${location.last}: $message';
  }
  return message;
}
