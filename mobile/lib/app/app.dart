import 'package:flutter/material.dart';

import '../core/network/api_client.dart';
import '../core/storage/preferences_storage.dart';
import '../core/storage/session_storage.dart';
import '../features/auth/auth_service.dart';
import '../features/auth/session_model.dart';
import 'routes.dart';
import 'theme.dart';

class GangaClothesApp extends StatefulWidget {
  const GangaClothesApp({
    this.sessionStorage,
    this.preferencesStorage,
    this.apiClient,
    super.key,
  });

  final SessionStorage? sessionStorage;
  final PreferencesStorage? preferencesStorage;
  final ApiClient? apiClient;

  @override
  State<GangaClothesApp> createState() => _GangaClothesAppState();
}

class _GangaClothesAppState extends State<GangaClothesApp> {
  late final SessionStorage _sessionStorage;
  late final PreferencesStorage _preferencesStorage;
  late final ApiClient _apiClient;
  late final AuthService _authService;
  final _navigatorKey = GlobalKey<NavigatorState>();
  Session? _session;
  bool _restoring = true;

  @override
  void initState() {
    super.initState();
    _sessionStorage = widget.sessionStorage ?? SessionStorage();
    _preferencesStorage =
        widget.preferencesStorage ?? PreferencesStorage.load();
    _apiClient =
        widget.apiClient ??
        ApiClient(
          tokenReader: _sessionStorage.readToken,
          onSessionExpired: _handleSessionExpired,
        );
    _authService = AuthService(
      apiClient: _apiClient,
      sessionStorage: _sessionStorage,
    );
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    final restored = await _sessionStorage.readSession();
    if (!mounted) return;
    setState(() {
      _session = restored;
      _restoring = false;
    });
  }

  void _setSession(Session? session) {
    if (!mounted) return;
    setState(() => _session = session);
  }

  Future<void> _logout() async {
    await _authService.logout();
    if (!mounted) return;
    _setSession(null);
    _navigatorKey.currentState?.pushNamedAndRemoveUntil(
      AppRoutes.login,
      (route) => false,
    );
  }

  Future<void> _handleSessionExpired() async {
    final current = _navigatorKey.currentState?.context;
    final currentRoute = current == null
        ? null
        : ModalRoute.of(current)?.settings.name;
    await _sessionStorage.clear();
    if (!mounted) return;
    final returnTo = AppRoutes.safeReturnTo(currentRoute);
    _setSession(null);
    _navigatorKey.currentState?.pushNamedAndRemoveUntil(
      AppRoutes.login,
      (route) => false,
      arguments: AuthRouteArguments(returnTo: returnTo),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_restoring) return const MaterialApp(home: _StartupView());
    return MaterialApp(
      title: 'GangaClothes',
      theme: GangaTheme.light(),
      navigatorKey: _navigatorKey,
      initialRoute: AppRoutes.catalog,
      onGenerateRoute: (settings) => AppRoutes.onGenerateRoute(
        settings,
        _session,
        authService: _authService,
        apiClient: _apiClient,
        preferencesStorage: _preferencesStorage,
        onSessionChanged: _setSession,
        onLogout: _logout,
      ),
    );
  }
}

class _StartupView extends StatelessWidget {
  const _StartupView();

  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: CircularProgressIndicator()));
}
