import 'package:lostvault/core/public/core.dart';
import 'package:lostvault/features/authentication/public/authentication.dart';
import 'package:lostvault/features/claims/public/claims.dart';
import 'package:lostvault/features/objects/public/objects.dart';
import 'package:lostvault/features/search/public/search.dart';

/// Raíz de composición: solo usa las fronteras public/ de cada módulo.
class AppDependencies {
  AppDependencies._(
      this.auth, this.objects, this.claim, this.search);

  final AuthenticationService auth;
  final ObjectService objects;
  final ClaimObjectUseCase claim;
  final SearchObjectsUseCase search;

  static late final AppDependencies instance;

  static void init() {
    final store = PrefsTokenStore();
    final api = ApiClient(baseUrl: AppConfig.apiBaseUrl, tokenStore: store);
    final objects = createObjectService(api, store);
    instance = AppDependencies._(
      createAuthenticationService(api, store),
      objects,
      createClaimObjectUseCase(api),
      SearchObjectsUseCase(objects),
    );
  }
}
