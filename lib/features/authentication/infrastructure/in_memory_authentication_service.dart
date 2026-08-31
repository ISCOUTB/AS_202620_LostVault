import '../application/authentication_service.dart';
import '../domain/auth_user.dart';

class InMemoryAuthenticationService implements AuthenticationService {
  AuthUser? _currentUser;

  @override
  AuthUser? get currentUser => _currentUser;

  @override
  Future<AuthUser?> signIn(String email) async {
    final normalizedEmail = email.trim();
    if (normalizedEmail.isEmpty) return null;

    _currentUser = AuthUser(id: normalizedEmail, email: normalizedEmail);
    return _currentUser;
  }

  @override
  Future<void> signOut() async {
    _currentUser = null;
  }
}
