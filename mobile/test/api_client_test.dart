import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/config/api_config.dart';
import 'package:mobile/core/network/api_client.dart';

void main() {
  test('injects a bearer header only for a non-empty token', () {
    final withToken = RequestOptions(path: '/test');
    ApiClient.applyBearerHeader(withToken, ' token-123 ');
    expect(withToken.headers['Authorization'], 'Bearer token-123');

    final withoutToken = RequestOptions(path: '/test');
    ApiClient.applyBearerHeader(withoutToken, null);
    expect(withoutToken.headers.containsKey('Authorization'), isFalse);
  });

  test('configures one Dio instance with JSON defaults and timeouts', () {
    final client = ApiClient(
      config: const ApiConfig(baseUrl: 'http://test/api'),
    );

    expect(client.dio.options.baseUrl, 'http://test/api');
    expect(client.dio.options.responseType, ResponseType.json);
    expect(client.dio.options.connectTimeout, const Duration(seconds: 10));
    expect(
      client.dio.interceptors.any(
        (interceptor) => interceptor is InterceptorsWrapper,
      ),
      isTrue,
    );
  });
}
