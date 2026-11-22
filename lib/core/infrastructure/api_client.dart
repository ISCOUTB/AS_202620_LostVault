import 'dart:convert';
import 'package:http/http.dart' as http;
import '../application/token_store.dart';
import '../domain/failure.dart';

/// Cliente HTTP único hacia la frontera definida en docs/contracts/lostvault-api.yaml.
class ApiClient {
  ApiClient({
    required this.baseUrl,
    required this.tokenStore,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final TokenStore tokenStore;
  final http.Client _client;

  Future<dynamic> get(String path) => _send('GET', path);

  Future<dynamic> post(String path,
          {Object? body, Map<String, String>? headers}) =>
      _send('POST', path, body: body, headers: headers);

  Future<dynamic> delete(String path) => _send('DELETE', path);

  Future<dynamic> _send(
    String method,
    String path, {
    Object? body,
    Map<String, String>? headers,
  }) async {
    final req = http.Request(method, Uri.parse('$baseUrl$path'));
    req.headers['Content-Type'] = 'application/json';
    req.headers['Accept'] = 'application/json';
    final t = tokenStore.token;
    if (t != null) req.headers['Authorization'] = 'Bearer $t';
    if (headers != null) req.headers.addAll(headers);
    if (body != null) req.body = jsonEncode(body);

    http.Response res;
    try {
      final streamed = await _client.send(req).timeout(const Duration(seconds: 20));
      res = await http.Response.fromStream(streamed);
    } catch (_) {
      throw Failure('NETWORK', friendlyMessage('NETWORK', 'Sin conexión'));
    }

    dynamic decoded;
    if (res.body.isNotEmpty) {
      try {
        decoded = jsonDecode(utf8.decode(res.bodyBytes));
      } catch (_) {
        decoded = null;
      }
    }

    if (res.statusCode >= 200 && res.statusCode < 300) return decoded;
    throw _toFailure(res.statusCode, decoded);
  }

  Failure _toFailure(int status, dynamic body) {
    String code = status == 401 ? 'UNAUTHENTICATED' : 'HTTP_$status';
    String message = 'Error $status';
    if (body is Map) {
      code = '${body['code'] ?? code}';
      final m = body['message'] ?? body['detail'] ?? body['error'];
      if (m is String) message = m;
    }
    return Failure(code, friendlyMessage(code, message), statusCode: status);
  }
}
