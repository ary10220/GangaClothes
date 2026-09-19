class ApiConfig {
  const ApiConfig({required this.baseUrl});

  static const localBaseUrl = 'https://gangaclothes-614p.onrender.com/api';
  static const productionBaseUrl = 'https://gangaclothes-614p.onrender.com/api';

  final String baseUrl;

  /// Selects a build-time URL. For a physical device or Android emulator,
  /// override localhost with a reachable host, for example:
  /// `--dart-define=API_BASE_URL=http://10.0.2.2:8001/api`.
  factory ApiConfig.fromEnvironment() {
    const override = String.fromEnvironment('API_BASE_URL');
    const environment = String.fromEnvironment('API_ENV');
    const isRelease = bool.fromEnvironment('dart.vm.product');

    if (override.trim().isNotEmpty) {
      return const ApiConfig(baseUrl: override);
    }
    if (environment.toLowerCase() == 'production' || isRelease) {
      return const ApiConfig(baseUrl: productionBaseUrl);
    }
    return const ApiConfig(baseUrl: localBaseUrl);
  }
}
