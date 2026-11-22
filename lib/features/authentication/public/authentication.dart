import 'package:lostvault/core/public/core.dart';
import '../application/authentication_service.dart';
import '../infrastructure/http_authentication_service.dart';

export '../application/authentication_service.dart';
export '../domain/session.dart';

AuthenticationService createAuthenticationService(
        ApiClient api, TokenStore store) =>
    HttpAuthenticationService(api, store);
