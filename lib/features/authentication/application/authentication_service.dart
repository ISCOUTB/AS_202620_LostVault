import '../domain/auth_user.dart';

abstract interface class AuthenticationService {
  Future<AuthUser?> signIn(String email);
}
