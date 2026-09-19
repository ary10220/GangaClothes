import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/routes.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/network/api_error.dart';
import 'package:mobile/core/storage/session_storage.dart';
import 'package:mobile/features/auth/auth_service.dart';
import 'package:mobile/features/auth/login/login_screen.dart';
import 'package:mobile/features/auth/recovery/recovery_screen.dart';
import 'package:mobile/features/auth/register/register_screen.dart';
import 'package:mobile/features/auth/session_model.dart';

void main() {
  testWidgets('login prevents duplicate submits and shows loading state', (
    tester,
  ) async {
    final request = Completer<Object?>();
    final api = _FakeApiClient((path, data) => request.future);
    final service = AuthService(
      apiClient: api,
      sessionStorage: SessionStorage(backend: _MemoryStorage()),
    );
    await tester.pumpWidget(
      MaterialApp(home: LoginScreen(authService: service)),
    );

    await tester.enterText(find.byType(TextFormField).at(0), 'ada@example.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'secret');
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pump();
    await tester.tap(find.text('Verificando…'));
    await tester.pump();

    expect(api.calls, 1);
    expect(find.text('Verificando…'), findsOneWidget);
    request.complete(_sessionJson());
    await tester.pumpAndSettle();
  });

  testWidgets('login footer actions stay centered in a vertical layout', (
    tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(390, 1000));
    await tester.pumpWidget(
      _narrowAuthApp(LoginScreen(authService: _authService())),
    );
    await tester.pumpAndSettle();

    final prompt = find.text('¿Cliente nuevo?');
    final createAccount = find.widgetWithText(TextButton, 'Crear cuenta');
    final catalog = find.widgetWithText(TextButton, 'Ver el catálogo');
    expect(prompt, findsOneWidget);
    expect(createAccount, findsOneWidget);
    expect(catalog, findsOneWidget);
    expect(find.text(' · '), findsNothing);
    _expectCenteredAndOrdered(tester, [prompt, createAccount, catalog]);
  });

  testWidgets(
    'registration footer actions stay centered in a vertical layout',
    (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.binding.setSurfaceSize(const Size(390, 1000));
      await tester.pumpWidget(
        _narrowAuthApp(RegisterScreen(authService: _authService())),
      );
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Ver el catálogo'));
      await tester.pump();

      final prompt = find.text('¿Ya tienes cuenta?');
      final login = find.widgetWithText(TextButton, 'Iniciar sesión');
      final catalog = find.widgetWithText(TextButton, 'Ver el catálogo');
      expect(prompt, findsOneWidget);
      expect(login, findsOneWidget);
      expect(catalog, findsOneWidget);
      expect(find.text(' · '), findsNothing);
      _expectCenteredAndOrdered(tester, [prompt, login, catalog]);
    },
  );

  testWidgets(
    'login maps 401 to invalid credentials while keeping the form visible',
    (tester) async {
      final api = _FakeApiClient(
        (path, data) async =>
            throw ApiError.fromStatus(401, {'detail': 'backend detail'}),
      );
      final service = AuthService(
        apiClient: api,
        sessionStorage: SessionStorage(backend: _MemoryStorage()),
      );
      await tester.pumpWidget(
        MaterialApp(home: LoginScreen(authService: service)),
      );

      await tester.enterText(
        find.byType(TextFormField).at(0),
        'ada@example.com',
      );
      await tester.enterText(find.byType(TextFormField).at(1), 'secret');
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      expect(find.text('Correo o contrasena incorrectos.'), findsOneWidget);
    },
  );

  testWidgets(
    'login persists the session and returns to the protected destination',
    (tester) async {
      final storage = SessionStorage(backend: _MemoryStorage());
      final service = AuthService(
        apiClient: _FakeApiClient((path, data) async => _sessionJson()),
        sessionStorage: storage,
      );
      Session? currentSession;
      await tester.pumpWidget(
        MaterialApp(
          home: LoginScreen(
            authService: service,
            returnTo: AppRoutes.cart,
            onSessionChanged: (session) => currentSession = session,
          ),
          onGenerateRoute: (settings) => AppRoutes.onGenerateRoute(
            settings,
            currentSession,
            authService: service,
          ),
        ),
      );
      await tester.enterText(
        find.byType(TextFormField).at(0),
        'ada@example.com',
      );
      await tester.enterText(find.byType(TextFormField).at(1), 'secret');
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      expect(await storage.readToken(), 'token');
      expect(find.text('Ruta preparada: cart'), findsOneWidget);
    },
  );

  testWidgets(
    'recovery transitions to code, shows cooldown, and allows another email',
    (tester) async {
      final api = _FakeApiClient((path, data) async {
        if (path == '/auth/recuperar') {
          return {
            'detail': 'Si el correo tiene una cuenta',
            'minutos': 15,
            'reenvio_en': 60,
          };
        }
        return {'detail': 'ok'};
      });
      final service = AuthService(
        apiClient: api,
        sessionStorage: SessionStorage(backend: _MemoryStorage()),
      );
      await tester.pumpWidget(
        MaterialApp(home: RecoveryScreen(authService: service)),
      );

      await tester.enterText(
        find.byType(TextFormField).first,
        'ada@example.com',
      );
      await tester.tap(find.text('Enviar código'));
      await tester.pumpAndSettle();

      expect(find.text('Revisa tu correo'), findsOneWidget);
      expect(find.textContaining('Vence en 15 minutos'), findsOneWidget);
      expect(find.textContaining('Puedes pedir otro en 60 s'), findsOneWidget);
      await tester.ensureVisible(find.text('Usar otro correo'));
      await tester.tap(find.text('Usar otro correo'));
      await tester.pump();
      expect(find.text('Recuperar contraseña'), findsOneWidget);
    },
  );

  testWidgets('recovery validates six digits and prefills login after reset', (
    tester,
  ) async {
    final api = _FakeApiClient((path, data) async {
      if (path == '/auth/recuperar') {
        return {
          'detail': 'Si el correo tiene una cuenta',
          'minutos': 15,
          'reenvio_en': 0,
        };
      }
      return {'detail': 'Tu contraseña se actualizó'};
    });
    final service = AuthService(
      apiClient: api,
      sessionStorage: SessionStorage(backend: _MemoryStorage()),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: RecoveryScreen(authService: service),
        onGenerateRoute: (settings) =>
            AppRoutes.onGenerateRoute(settings, null, authService: service),
      ),
    );

    await tester.enterText(find.byType(TextFormField).first, 'ada@example.com');
    await tester.tap(find.text('Enviar código'));
    await tester.pumpAndSettle();
    expect(find.text('Reenviar código'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).at(0), '12345');
    await tester.enterText(find.byType(TextFormField).at(1), 'Abcdef1!');
    await tester.enterText(find.byType(TextFormField).at(2), 'Abcdef1!');
    final resetButton = find.widgetWithText(FilledButton, 'Cambiar contraseña');
    await tester.ensureVisible(resetButton);
    await tester.tap(resetButton);
    await tester.pump();
    expect(find.text('El código son 6 números.'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).at(0), '123456');
    await tester.ensureVisible(resetButton);
    await tester.tap(resetButton);
    await tester.pumpAndSettle();
    expect(find.byType(LoginScreen), findsOneWidget);
    expect(
      tester
          .widget<TextFormField>(find.byType(TextFormField).first)
          .controller!
          .text,
      'ada@example.com',
    );
  });
}

AuthService _authService() => AuthService(
  apiClient: _FakeApiClient((path, data) async => _sessionJson()),
  sessionStorage: SessionStorage(backend: _MemoryStorage()),
);

Widget _narrowAuthApp(Widget child) => MaterialApp(
  home: MediaQuery(
    data: const MediaQueryData(size: Size(390, 1000)),
    child: child,
  ),
);

void _expectCenteredAndOrdered(WidgetTester tester, List<Finder> widgets) {
  final screenCenter = tester.getSize(find.byType(Scaffold).first).width / 2;
  final centers = widgets.map(tester.getCenter).toList();
  for (final center in centers) {
    expect(center.dx, closeTo(screenCenter, 1));
  }
  for (var index = 1; index < centers.length; index++) {
    expect(centers[index].dy, greaterThan(centers[index - 1].dy));
  }
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
  int calls = 0;

  @override
  Future<Response<T>> request<T>(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    calls++;
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
