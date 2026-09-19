import '../../core/network/api_client.dart';
import '../../core/storage/session_storage.dart';
import 'session_model.dart';

class RegisterRequest {
  const RegisterRequest({
    required this.name,
    required this.email,
    required this.password,
    this.lastName,
    this.phone,
  });

  final String name;
  final String email;
  final String password;
  final String? lastName;
  final String? phone;

  Map<String, dynamic> toJson() => {
    'nombre': name,
    if (lastName != null && lastName!.trim().isNotEmpty) 'apellido': lastName,
    'email': email,
    'password': password,
    if (phone != null && phone!.trim().isNotEmpty) 'telefono': phone,
  };
}

class RecoveryResponse {
  const RecoveryResponse({
    required this.detail,
    required this.minutes,
    required this.resendAfter,
  });

  final String detail;
  final int minutes;
  final int resendAfter;

  /// Backend names retained as aliases at the feature boundary.
  int get minutos => minutes;
  int get reenvioEn => resendAfter;

  factory RecoveryResponse.fromJson(Map<String, dynamic> json) =>
      RecoveryResponse(
        detail: json['detail'] as String? ?? '',
        minutes: _intValue(json['minutos']) ?? 15,
        resendAfter: _intValue(json['reenvio_en']) ?? 60,
      );
}

class ResetResponse {
  const ResetResponse({required this.detail});

  final String detail;

  factory ResetResponse.fromJson(Map<String, dynamic> json) =>
      ResetResponse(detail: json['detail'] as String? ?? '');
}

class AuthService {
  const AuthService({required this.apiClient, required this.sessionStorage});

  final ApiClient apiClient;
  final SessionStorage sessionStorage;

  Future<Session> login(String email, String password) async {
    final response = await apiClient.request<Map<String, dynamic>>(
      '/auth/login',
      method: 'POST',
      data: {'email': email, 'password': password},
    );
    final session = Session.fromJson(_map(response.data));
    await sessionStorage.saveSession(session);
    return session;
  }

  Future<Session> register(RegisterRequest request) async {
    final response = await apiClient.request<Map<String, dynamic>>(
      '/auth/register',
      method: 'POST',
      data: request.toJson(),
    );
    final session = Session.fromJson(_map(response.data));
    await sessionStorage.saveSession(session);
    return session;
  }

  Future<RecoveryResponse> requestRecovery(String email) async {
    final response = await apiClient.request<Map<String, dynamic>>(
      '/auth/recuperar',
      method: 'POST',
      data: {'email': email},
    );
    return RecoveryResponse.fromJson(_map(response.data));
  }

  Future<ResetResponse> resetPassword({
    required String email,
    required String code,
    required String password,
  }) async {
    final response = await apiClient.request<Map<String, dynamic>>(
      '/auth/restablecer',
      method: 'POST',
      data: {'email': email, 'codigo': code, 'password': password},
    );
    return ResetResponse.fromJson(_map(response.data));
  }

  /// Server logout is audit-only. Local state is cleared even if it fails.
  Future<void> logout() async {
    try {
      if (await sessionStorage.readToken() != null) {
        await apiClient.request<Map<String, dynamic>>(
          '/auth/logout',
          method: 'POST',
          data: const {},
        );
      }
    } catch (_) {
      // An expired token or unavailable API must not block local logout.
    } finally {
      await sessionStorage.clear();
    }
  }
}

Map<String, dynamic> _map(Object? value) {
  if (value is Map<String, dynamic>) return value;
  if (value is Map) return Map<String, dynamic>.from(value);
  throw const FormatException('Invalid authentication response');
}

int? _intValue(Object? value) {
  if (value is int) return value;
  return value is String ? int.tryParse(value) : null;
}
