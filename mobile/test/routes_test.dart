import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/routes.dart';
import 'package:mobile/features/auth/session_model.dart';

void main() {
  const user = User(id: 1, name: 'Cliente', email: 'cliente@example.com');
  const session = Session(accessToken: 'token', user: user);

  test('redirects protected routes to login without a session', () {
    expect(AppRoutes.destinationFor(AppRoutes.cart, null), AppRoutes.login);
  });

  test('sends authenticated users to catalog from guest routes', () {
    expect(
      AppRoutes.destinationFor(AppRoutes.login, session),
      AppRoutes.catalog,
    );
  });

  test('accepts only known internal return destinations', () {
    expect(AppRoutes.safeReturnTo('/cart'), AppRoutes.cart);
    expect(AppRoutes.safeReturnTo('/catalogo'), AppRoutes.catalog);
    expect(AppRoutes.safeReturnTo('https://evil.example'), isNull);
    expect(AppRoutes.safeReturnTo('//evil.example'), isNull);
    expect(AppRoutes.safeReturnTo('/cart?next=https://evil.example'), isNull);
    expect(AppRoutes.safeReturnTo('/unknown'), isNull);
  });
}
