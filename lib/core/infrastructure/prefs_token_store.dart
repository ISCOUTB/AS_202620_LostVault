import 'package:shared_preferences/shared_preferences.dart';
import '../application/token_store.dart';

class PrefsTokenStore implements TokenStore {
  String? _token;
  String? _email;

  @override
  String? get token => _token;

  @override
  String? get email => _email;

  @override
  Future<void> load() async {
    final p = await SharedPreferences.getInstance();
    _token = p.getString('token');
    _email = p.getString('email');
  }

  @override
  Future<void> save({required String token, required String email}) async {
    _token = token;
    _email = email;
    final p = await SharedPreferences.getInstance();
    await p.setString('token', token);
    await p.setString('email', email);
  }

  @override
  Future<void> clear() async {
    _token = null;
    _email = null;
    final p = await SharedPreferences.getInstance();
    await p.remove('token');
    await p.remove('email');
  }
}
