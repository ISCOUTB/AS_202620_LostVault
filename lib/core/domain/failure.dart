/// Error de negocio/transporte con código estable (ver Problem en el contrato OpenAPI).
class Failure implements Exception {
  const Failure(this.code, this.message, {this.statusCode});

  final String code;
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

const Map<String, String> _friendly = {
  'UNAUTHENTICATED': 'Debes iniciar sesión para continuar.',
  'OBJECT_NOT_FOUND': 'El objeto no existe.',
  'OBJECT_ALREADY_CLAIMED': 'Este objeto ya fue reclamado.',
  'IDENTITY_NOT_VERIFIED': 'No pudimos verificar tu identidad.',
  'IDEMPOTENCY_KEY_REUSED': 'Esta solicitud ya se usó para otro objeto.',
  'INVALID_IDEMPOTENCY_KEY': 'Identificador de solicitud inválido.',
  'FORBIDDEN': 'Solo quien reportó el objeto puede borrarlo.',
  'INVALID_CREDENTIALS': 'Correo o contraseña incorrectos.',
  'NETWORK': 'No se pudo conectar con el servidor.',
};

String friendlyMessage(String code, String fallback) =>
    _friendly[code] ?? fallback;
