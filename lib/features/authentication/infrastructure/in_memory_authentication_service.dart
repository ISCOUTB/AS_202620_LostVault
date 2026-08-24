import '../application/authentication_service.dart';
import '../domain/auth_user.dart';

class InMemoryAuthenticationService implements AuthenticationService {
  @override
  Future<AuthUser?> signIn(String email) async => AuthUser(id: email, email: email);
}
