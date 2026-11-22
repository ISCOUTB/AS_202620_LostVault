import 'package:lostvault/core/public/core.dart';
import '../application/claim_service.dart';
import '../domain/claim.dart';

class HttpClaimService implements ClaimService {
  HttpClaimService(this._api);
  final ApiClient _api;

  // POST /v1/objects/{objectId}/claims  -> 201 / 200 {objectId, userId, verified}
  @override
  Future<Claim> claim(String objectId, {required String idempotencyKey}) async {
    final res = await _api.post(
      '/v1/objects/$objectId/claims',
      headers: {'Idempotency-Key': idempotencyKey},
    );
    final m = res is Map ? res : const {};
    return Claim(
      objectId: '${m['objectId'] ?? objectId}',
      userId: '${m['userId'] ?? ''}',
      verified: m['verified'] == true,
    );
  }
}
