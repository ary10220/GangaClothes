import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/storage/session_storage.dart';
import 'package:mobile/features/auth/auth_service.dart';

void main() {
  test('sends backend field names and parses login session', () async {
    final api = _FakeApiClient((path, data) async {
      expect(path, '/auth/login');
      expect(data, {'email': 'ada@example.com', 'password': 'Secret1!'});
      return _sessionJson();
    });
    final storage = SessionStorage(backend: _MemoryStorage());
    final service = AuthService(apiClient: api, sessionStorage: storage);

    final session = await service.login('ada@example.com', 'Secret1!');

    expect(session.user.email, 'ada@example.com');
    expect(await storage.readToken(), 'token');
  });

  test(
    'sends optional registration fields and parses recovery metadata',
    () async {
      final requests = <String, Map<String, dynamic>>{};
      final api = _FakeApiClient((path, data) async {
        requests[path] = Map<String, dynamic>.from(data as Map);
        if (path == '/auth/register') return _sessionJson();
        return {
          'detail': 'Si el correo tiene una cuenta',
          'minutos': 15,
          'reenvio_en': 60,
        };
      });
      final storage = SessionStorage(backend: _MemoryStorage());
      final service = AuthService(apiClient: api, sessionStorage: storage);

      await service.register(
        const RegisterRequest(
          name: 'Ada',
          email: 'ada@example.com',
          password: 'Secret1!',
          lastName: 'Lovelace',
          phone: '70012345',
        ),
      );
      final recovery = await service.requestRecovery('ada@example.com');

      expect(requests['/auth/register'], {
        'nombre': 'Ada',
        'apellido': 'Lovelace',
        'email': 'ada@example.com',
        'password': 'Secret1!',
        'telefono': '70012345',
      });
      expect(recovery.detail, contains('Si el correo'));
      expect(recovery.minutes, 15);
      expect(recovery.resendAfter, 60);
      expect(await storage.readToken(), 'token');
    },
  );

  test('logout clears local session when server logout fails', () async {
    final storageBackend = _MemoryStorage()
      ..values[SessionStorage.tokenKey] = 'token'
      ..values[SessionStorage.userKey] =
          '{"id":1,"nombre":"Ada","email":"ada@example.com"}';
    final api = _FakeApiClient((path, data) async {
      throw ApiError.fromStatus(500, {'detail': 'offline'});
    });
    final service = AuthService(
      apiClient: api,
      sessionStorage: SessionStorage(backend: storageBackend),
    );

    await service.logout();

    expect(storageBackend.values, isEmpty);
  });

  test('preserves status and backend detail for auth failures', () async {
    final api = _FakeApiClient((path, data) async {
      throw ApiError.fromStatus(401, {
        'detail': 'Correo o contrasena incorrectos',
      });
    });
    final service = AuthService(
      apiClient: api,
      sessionStorage: SessionStorage(backend: _MemoryStorage()),
    );

    expect(
      () => service.login('bad@example.com', 'badbad'),
      throwsA(
        isA<ApiError>().having((error) => error.statusCode, 'status', 401),
      ),
    );
  });
}

Map<String, dynamic> _sessionJson() => {
  'access_token': 'token',
  'token_type': 'bearer',
  'usuario': {
    'id': 1,
    'nombre': 'Ada',
    'apellido': null,
    'email': 'ada@example.com',
    'roles': ['cliente'],
    'permisos': [],
  },
};

class _FakeApiClient extends ApiClient {
  _FakeApiClient(this.handler) : super(dio: Dio());

  final Future<Object?> Function(String path, Object? data) handler;

  @override
  Future<Response<T>> request<T>(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    final value = await handler(path, data);
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: value as T,
      statusCode: 200,
    );
  }
}

class _MemoryStorage implements SecureStorageBackend {
  final values = <String, String>{};

  @override
  Future<String?> read({required String key}) async => values[key];

  @override
  Future<void> write({required String key, required String value}) async =>
      values[key] = value;

  @override
  Future<void> delete({required String key}) async => values.remove(key);
}
