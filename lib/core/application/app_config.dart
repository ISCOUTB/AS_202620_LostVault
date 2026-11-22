class AppConfig {
  /// Se puede sobreescribir: flutter run --dart-define=API_BASE_URL=http://...
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue:
        'http://lostvault-lostvaultapi-1k8ly4-3d8075-144-24-4-187.sslip.io',
  );
}
