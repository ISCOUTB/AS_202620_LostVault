import '../application/claim_service.dart';
import '../domain/claim.dart';

class InMemoryClaimService implements ClaimService {
  @override
  Future<Claim> requestClaim({required String objectId, required String userId, required bool identityVerified}) async {
    if (!identityVerified) {
      throw StateError('La reclamación requiere verificación de identidad.');
    }
    return Claim(objectId: objectId, userId: userId, verified: true);
  }
}
