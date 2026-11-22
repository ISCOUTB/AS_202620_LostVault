import 'dart:math';
import '../domain/claim.dart';
import 'claim_service.dart';

/// Orquesta la reclamación. La misma intención reutiliza la Idempotency-Key
/// en cada reintento (contrato: vigencia 24 h por usuario).
class ClaimObjectUseCase {
  ClaimObjectUseCase(this._service);
  final ClaimService _service;
  final Map<String, String> _keys = {};
  final Random _rnd = Random.secure();

  String _uuidV4() {
    final b = List<int>.generate(16, (_) => _rnd.nextInt(256));
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    final h = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
    return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-'
        '${h.substring(16, 20)}-${h.substring(20)}';
  }

  Future<Claim> call(String objectId) async {
    final key = _keys.putIfAbsent(objectId, _uuidV4);
    return _service.claim(objectId, idempotencyKey: key);
  }
}
