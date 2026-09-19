import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/app.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/core/storage/preferences_storage.dart';
import 'package:mobile/core/storage/session_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets('boots the session-aware app shell', (tester) async {
    SharedPreferences.setMockInitialValues({});
    final preferences = await SharedPreferences.getInstance();
    await tester.pumpWidget(
      GangaClothesApp(
        sessionStorage: SessionStorage(backend: _EmptyStorage()),
        preferencesStorage: PreferencesStorage.fromInstance(preferences),
        apiClient: _CatalogApi(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('GangaClothes'), findsWidgets);
    expect(find.text('Prendas publicadas'), findsOneWidget);
    expect(find.text('Todavía no hay prendas publicadas.'), findsOneWidget);
  });
}

class _EmptyStorage implements SecureStorageBackend {
  @override
  Future<String?> read({required String key}) async => null;

  @override
  Future<void> write({required String key, required String value}) async {}

  @override
  Future<void> delete({required String key}) async {}
}

class _CatalogApi extends ApiClient {
  _CatalogApi() : super(dio: Dio());

  @override
  Future<Response<T>> request<T>(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: <Object?>[] as T,
      statusCode: 200,
    );
  }
}
