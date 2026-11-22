/// Puerto de persistencia de la sesión (token + correo).
abstract class TokenStore {
  String? get token;
  String? get email;
  Future<void> load();
  Future<void> save({required String token, required String email});
  Future<void> clear();
}
