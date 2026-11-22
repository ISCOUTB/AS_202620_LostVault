import 'package:lostvault/core/public/core.dart';
import '../application/authentication_service.dart';
import '../domain/session.dart';

class HttpAuthenticationService implements AuthenticationService {
  HttpAuthenticationService(this._api, this._store);
  final ApiClient _api;
  final TokenStore _store;

  @override
  Future<Session?> restore() async {
    await _store.load();
    final t = _store.token;
    final e = _store.email;
    if (t == null || e == null) return null;
    return Session(email: e, token: t);
  }

  // POST /v1/auth/login  (ASUMIDO: cuerpo {email, password})
  @override
  Future<Session> login(String email, String password) async {
    final res = await _api.post('/v1/auth/login',
        body: {'email': email, 'password': password});
    final token = res is Map
        ? (res['token'] ?? res['accessToken'] ?? res['access_token'])
        : null;
    if (token == null) {
      throw const Failure('LOGIN_INVALID_RESPONSE', 'La API no devolvió token.');
    }
    await _store.save(token: '$token', email: email);
    return Session(email: email, token: '$token');
  }

  @override
  Future<void> logout() => _store.clear();
}
