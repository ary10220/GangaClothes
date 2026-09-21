import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/routes.dart';
import 'package:mobile/features/auth/session_model.dart';

void main() {
  const user = User(
    id: 1,
    name: 'Cliente',
    email: 'cliente@example.com',
    roles: ['cliente'],
  );
  const session = Session(accessToken: 'token', user: user);

  test('redirects protected routes to login without a session', () {
    expect(AppRoutes.destinationFor(AppRoutes.cart, null), AppRoutes.login);
    expect(
      AppRoutes.destinationFor(AppRoutes.purchaseHistory, null),
      AppRoutes.login,
    );
    expect(
      AppRoutes.destinationFor(AppRoutes.reservations, null),
      AppRoutes.login,
    );
  });

  test('sends authenticated users to catalog from guest routes', () {
    expect(
      AppRoutes.destinationFor(AppRoutes.login, session),
      AppRoutes.catalog,
    );
  });

  test('allows reservations only for authenticated customer roles', () {
    expect(
      AppRoutes.destinationFor(AppRoutes.reservations, session),
      AppRoutes.reservations,
    );
    expect(
      AppRoutes.destinationFor(AppRoutes.shipmentTracking, session),
      AppRoutes.shipmentTracking,
    );
    expect(
      AppRoutes.destinationFor(AppRoutes.purchaseHistory, session),
      AppRoutes.purchaseHistory,
    );
    const staff = Session(
      accessToken: 'token',
      user: User(
        id: 2,
        name: 'Encargado',
        email: 'staff@example.com',
        roles: ['encargado'],
      ),
    );
    expect(
      AppRoutes.destinationFor(AppRoutes.reservations, staff),
      AppRoutes.catalog,
    );
    expect(AppRoutes.destinationFor(AppRoutes.cart, staff), AppRoutes.catalog);
    expect(
      AppRoutes.destinationFor(AppRoutes.purchaseHistory, staff),
      AppRoutes.catalog,
    );
    expect(
      AppRoutes.destinationFor(AppRoutes.shipmentTracking, staff),
      AppRoutes.catalog,
    );
    expect(
      AppRoutes.destinationFor(AppRoutes.cartPayment, session),
      AppRoutes.cartPayment,
    );
  });

  test('accepts only known internal return destinations', () {
    expect(AppRoutes.safeReturnTo('/cart'), AppRoutes.cart);
    expect(AppRoutes.safeReturnTo('/catalogo'), AppRoutes.catalog);
    expect(AppRoutes.safeReturnTo('/mis-compras'), AppRoutes.purchaseHistory);
    expect(AppRoutes.safeReturnTo('https://evil.example'), isNull);
    expect(AppRoutes.safeReturnTo('//evil.example'), isNull);
    expect(AppRoutes.safeReturnTo('/cart?next=https://evil.example'), isNull);
    expect(AppRoutes.safeReturnTo('/unknown'), isNull);
  });
}
