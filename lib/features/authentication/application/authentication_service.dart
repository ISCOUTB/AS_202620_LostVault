import '../domain/session.dart';

abstract class AuthenticationService {
  /// Sesión guardada del arranque anterior (null si no hay).
  Future<Session?> restore();
  Future<Session> login(String email, String password);
  Future<void> logout();
}
