import 'package:flutter/material.dart';

import '../core/network/api_client.dart';
import '../core/storage/preferences_storage.dart';
import '../features/auth/auth_service.dart';
import '../features/auth/login/login_screen.dart';
import '../features/auth/recovery/recovery_screen.dart';
import '../features/auth/register/register_screen.dart';
import '../features/auth/session_model.dart';
import '../features/catalog/catalog_screen.dart';
import '../features/cart/cart_screen.dart';
import '../features/purchase_history/purchase_history_screen.dart';
import '../features/reservations/reservations_screen.dart';
import '../features/showcase/theme_showcase_screen.dart';

typedef SessionChanged = void Function(Session? session);

class AuthRouteArguments {
  const AuthRouteArguments({this.returnTo, this.email});

  final String? returnTo;
  final String? email;
}

abstract final class AppRoutes {
  static const login = 'login';
  static const register = 'register';
  static const recovery = 'recovery';
  static const catalog = 'catalog';
  static const catalogDetail = 'catalog/detail';
  static const reservations = 'reservations';
  static const purchaseHistory = 'purchase-history';
  static const cart = 'cart';
  static const cartPayment = 'cart/payment';

  static const _known = {
    login,
    register,
    recovery,
    catalog,
    catalogDetail,
    reservations,
    purchaseHistory,
    cart,
    cartPayment,
  };
  static const _returnDestinations = {
    catalog,
    catalogDetail,
    reservations,
    purchaseHistory,
    cart,
    cartPayment,
  };

  /// Only known in-app destinations can be carried through authentication.
  /// URLs, query strings, traversal, and arbitrary route names are rejected.
  static String? safeReturnTo(String? value) {
    if (value == null) return null;
    var candidate = value.trim();
    if (candidate.startsWith('/')) candidate = candidate.substring(1);
    if (candidate.isEmpty ||
        candidate.startsWith('/') ||
        candidate.contains('://')) {
      return null;
    }
    const aliases = {
      'catalogo': catalog,
      'mis-reservas': reservations,
      'mis-compras': purchaseHistory,
      'carrito': cart,
    };
    candidate = aliases[candidate] ?? candidate;
    if (candidate.contains('?') ||
        candidate.contains('#') ||
        candidate.contains('..')) {
      return null;
    }
    return _returnDestinations.contains(candidate) ? candidate : null;
  }

  static String destinationFor(String requested, Session? session) {
    final route = _normalize(requested) ?? catalog;
    const protected = {reservations, purchaseHistory, cart, cartPayment};
    const guestOnly = {login, register, recovery};
    if (protected.contains(route) && session == null) return login;
    if ((route == reservations ||
            route == purchaseHistory ||
            route == cart ||
            route == cartPayment) &&
        !(session?.user.roles.contains('cliente') ?? false)) {
      return catalog;
    }
    if (guestOnly.contains(route) && session != null) return catalog;
    return _known.contains(route) ? route : catalog;
  }

  static Route<dynamic> onGenerateRoute(
    RouteSettings settings,
    Session? session, {
    AuthService? authService,
    ApiClient? apiClient,
    PreferencesStorage? preferencesStorage,
    SessionChanged? onSessionChanged,
    VoidCallback? onLogout,
  }) {
    final requested = _normalize(settings.name ?? catalog) ?? catalog;
    final destination = destinationFor(requested, session);
    final arguments = settings.arguments;
    final supplied = arguments is AuthRouteArguments ? arguments : null;
    final returnTo = destination == login && requested != login
        ? safeReturnTo(requested)
        : safeReturnTo(supplied?.returnTo);
    final service =
        authService ??
        (throw StateError('App routes require the app AuthService instance.'));

    Widget page;
    switch (destination) {
      case login:
        page = LoginScreen(
          authService: service,
          onSessionChanged: onSessionChanged,
          returnTo: returnTo,
          initialEmail: supplied?.email,
        );
      case register:
        page = RegisterScreen(
          authService: service,
          onSessionChanged: onSessionChanged,
          returnTo: safeReturnTo(supplied?.returnTo),
        );
      case recovery:
        page = RecoveryScreen(
          authService: service,
          initialEmail: supplied?.email,
        );
      case catalog:
        if (apiClient == null || preferencesStorage == null) {
          throw StateError(
            'Catalog routes require the app ApiClient and PreferencesStorage.',
          );
        }
        page = CatalogScreen(
          apiClient: apiClient,
          preferencesStorage: preferencesStorage,
          session: session,
          onLogout: onLogout,
        );
      case reservations:
        if (apiClient == null) {
          throw StateError('Reservation routes require the app ApiClient.');
        }
        page = ReservationsScreen(
          apiClient: apiClient,
          session: session,
          onLogout: onLogout,
        );
      case purchaseHistory:
        if (apiClient == null) {
          throw StateError(
            'Purchase history routes require the app ApiClient.',
          );
        }
        page = PurchaseHistoryScreen(
          apiClient: apiClient,
          session: session,
          onLogout: onLogout,
        );
      case cart:
      case cartPayment:
        page = apiClient == null
            ? PlaceholderScreen(
                routeName: destination,
                session: session,
                returnTo: returnTo,
                onLogout: onLogout,
              )
            : CartScreen(
                apiClient: apiClient,
                session: session,
                openPayment: destination == cartPayment,
                onLogout: onLogout,
              );
      default:
        page = PlaceholderScreen(
          routeName: destination,
          session: session,
          returnTo: returnTo,
          onLogout: onLogout,
        );
    }

    return MaterialPageRoute<void>(
      settings: RouteSettings(name: destination, arguments: settings.arguments),
      builder: (_) => page,
    );
  }

  static String? _normalize(String value) {
    final candidate = value.startsWith('/') ? value.substring(1) : value;
    return _known.contains(candidate) ? candidate : null;
  }
}

class PlaceholderScreen extends StatelessWidget {
  const PlaceholderScreen({
    required this.routeName,
    required this.session,
    this.returnTo,
    this.onLogout,
    super.key,
  });

  final String routeName;
  final Session? session;
  final String? returnTo;
  final VoidCallback? onLogout;

  @override
  Widget build(BuildContext context) => ThemeShowcaseScreen(
    routeName: routeName,
    session: session,
    returnTo: returnTo,
    onLogout: onLogout,
  );
}
