import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/storage/session_storage.dart';
import 'package:mobile/features/auth/session_model.dart';

void main() {
  final session = Session(
    accessToken: 'token-123',
    user: const User(
      id: 7,
      name: 'Ada',
      lastName: 'Lovelace',
      email: 'ada@example.com',
      roles: ['cliente'],
      permissions: ['catalogo:leer'],
    ),
  );

  test('stores and restores a session', () async {
    final backend = _MemorySecureStorage();
    final storage = SessionStorage(backend: backend);

    await storage.saveSession(session);

    expect(await storage.readSession(), isA<Session>());
    final restored = await storage.readSession();
    expect(restored!.accessToken, 'token-123');
    expect(restored.user.email, 'ada@example.com');
  });

  test('returns null and clears a missing session', () async {
    final backend = _MemorySecureStorage()
      ..values[SessionStorage.userKey] = '{"id": 7}';
    final storage = SessionStorage(backend: backend);

    expect(await storage.readSession(), isNull);
    expect(backend.values, isEmpty);
  });

  test('returns null and clears corrupt session data', () async {
    final backend = _MemorySecureStorage()
      ..values[SessionStorage.tokenKey] = 'token-123'
      ..values[SessionStorage.userKey] = '{not-json';
    final storage = SessionStorage(backend: backend);

    expect(await storage.readSession(), isNull);
    expect(backend.values, isEmpty);
  });

  test('clear removes both session values', () async {
    final backend = _MemorySecureStorage();
    final storage = SessionStorage(backend: backend);
    await storage.saveSession(session);

    await storage.clear();

    expect(backend.values, isEmpty);
  });
}

class _MemorySecureStorage implements SecureStorageBackend {
  final values = <String, String>{};

  @override
  Future<String?> read({required String key}) async => values[key];

  @override
  Future<void> write({required String key, required String value}) async {
    values[key] = value;
  }

  @override
  Future<void> delete({required String key}) async {
    values.remove(key);
  }
}
