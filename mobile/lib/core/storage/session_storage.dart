import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../features/auth/session_model.dart';

abstract interface class SecureStorageBackend {
  Future<String?> read({required String key});

  Future<void> write({required String key, required String value});

  Future<void> delete({required String key});
}

class SessionStorage {
  SessionStorage({SecureStorageBackend? backend})
    : _backend =
          backend ?? _FlutterSecureStorageBackend(FlutterSecureStorage());

  static const tokenKey = 'gc_token';
  static const userKey = 'gc_usuario';

  final SecureStorageBackend _backend;

  Future<String?> readToken() async {
    try {
      final token = await _backend.read(key: tokenKey);
      return token?.trim().isEmpty == true ? null : token;
    } catch (_) {
      return null;
    }
  }

  Future<Session?> readSession() async {
    try {
      final token = await _backend.read(key: tokenKey);
      final rawUser = await _backend.read(key: userKey);
      if (token == null || token.trim().isEmpty || rawUser == null) {
        await _clearIgnoringErrors();
        return null;
      }

      final decoded = jsonDecode(rawUser);
      if (decoded is! Map) throw const FormatException('Invalid stored user');
      return Session(
        accessToken: token,
        user: User.fromJson(Map<String, dynamic>.from(decoded)),
      );
    } catch (_) {
      await _clearIgnoringErrors();
      return null;
    }
  }

  Future<void> saveSession(Session session) async {
    try {
      await _backend.write(key: tokenKey, value: session.accessToken);
      await _backend.write(
        key: userKey,
        value: jsonEncode(session.user.toJson()),
      );
    } catch (_) {
      await _clearIgnoringErrors();
      rethrow;
    }
  }

  Future<void> clear() async {
    await _backend.delete(key: tokenKey);
    await _backend.delete(key: userKey);
  }

  Future<void> _clearIgnoringErrors() async {
    try {
      await clear();
    } catch (_) {
      // A corrupt or unavailable store must not prevent app startup.
    }
  }
}

class _FlutterSecureStorageBackend implements SecureStorageBackend {
  const _FlutterSecureStorageBackend(this.storage);

  final FlutterSecureStorage storage;

  @override
  Future<String?> read({required String key}) => storage.read(key: key);

  @override
  Future<void> write({required String key, required String value}) =>
      storage.write(key: key, value: value);

  @override
  Future<void> delete({required String key}) => storage.delete(key: key);
}
