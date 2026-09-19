import 'dart:async';

import 'package:dio/dio.dart';

import '../config/api_config.dart';
import 'api_error.dart';

typedef TokenReader = Future<String?> Function();
typedef SessionExpiredHandler = FutureOr<void> Function();

class ApiClient {
  ApiClient({
    ApiConfig? config,
    TokenReader? tokenReader,
    this.onSessionExpired,
    Dio? dio,
  }) : dio = dio ?? Dio(),
       _tokenReader = tokenReader ?? _emptyTokenReader {
    final selectedConfig = config ?? ApiConfig.fromEnvironment();
    if (this.dio.options.baseUrl.isEmpty) {
      this.dio.options.baseUrl = selectedConfig.baseUrl;
    }
    this.dio.options.connectTimeout = const Duration(seconds: 10);
    this.dio.options.receiveTimeout = const Duration(seconds: 20);
    this.dio.options.sendTimeout = const Duration(seconds: 20);
    this.dio.options.responseType = ResponseType.json;
    this.dio.options.headers['Accept'] = 'application/json';
    this.dio.options.headers['Content-Type'] = 'application/json';
    this.dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          applyBearerHeader(options, await _tokenReader());
          handler.next(options);
        },
      ),
    );
  }

  final Dio dio;
  final TokenReader _tokenReader;
  final SessionExpiredHandler? onSessionExpired;

  /// Applies the same rule used by the interceptor and is intentionally small
  /// enough to verify without making a network request.
  static void applyBearerHeader(RequestOptions options, String? token) {
    final value = token?.trim();
    if (value == null || value.isEmpty) {
      options.headers.remove('Authorization');
      return;
    }
    options.headers['Authorization'] = 'Bearer $value';
  }

  Future<Response<T>> request<T>(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      final response = await dio.request<T>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: (options ?? Options()).copyWith(method: method),
        cancelToken: cancelToken,
      );
      final statusCode = response.statusCode ?? 0;
      if (statusCode >= 400 || statusCode == 0) {
        await _notifySessionExpired(path, statusCode);
        throw ApiError.fromStatus(statusCode, response.data);
      }
      return response;
    } on ApiError {
      rethrow;
    } on DioException catch (error) {
      await _notifySessionExpired(path, error.response?.statusCode ?? 0);
      throw ApiError.fromDioException(error);
    }
  }

  Future<void> _notifySessionExpired(String path, int statusCode) async {
    if (statusCode != 401 || path.startsWith('/auth/')) return;
    try {
      await onSessionExpired?.call();
    } catch (_) {
      // Error normalization must still reach the feature that made the call.
    }
  }
}

Future<String?> _emptyTokenReader() async => null;
