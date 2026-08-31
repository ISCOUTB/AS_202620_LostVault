import '../domain/auth_user.dart';

abstract interface class AuthenticationService {
  AuthUser? get currentUser;

  Future<AuthUser?> signIn(String email);

  Future<void> signOut();
}
