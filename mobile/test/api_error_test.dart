import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:mobile/core/network/api_error.dart';

void main() {
  test('preserves backend detail text and status', () {
    final error = ApiError.fromStatus(403, {'detail': 'Sucursal bloqueada'});

    expect(error.statusCode, 403);
    expect(error.message, 'Sucursal bloqueada');
  });

  test('formats validation details from FastAPI', () {
    final error = ApiError.fromStatus(422, {
      'detail': [
        {
          'loc': ['body', 'email'],
          'msg': 'value is not a valid email',
        },
        {
          'loc': ['body', 'password'],
          'msg': 'field required',
        },
      ],
    });

    expect(error.message, contains('email: value is not a valid email'));
    expect(error.message, contains('password: field required'));
  });

  test('maps network, auth, payment, and server statuses', () {
    expect(ApiError.fromStatus(0, null).isNetworkError, isTrue);
    expect(
      ApiError.fromDioException(
        DioException(
          requestOptions: RequestOptions(path: '/test'),
          message: 'connection refused',
        ),
      ).message,
      'No se pudo contactar al servidor.',
    );
    expect(ApiError.fromStatus(401, null).message, contains('sesión'));
    expect(ApiError.fromStatus(402, null).message, contains('rechazado'));
    expect(ApiError.fromStatus(500, null).message, contains('servidor'));
  });
}
