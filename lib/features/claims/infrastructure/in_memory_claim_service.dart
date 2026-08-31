import '../application/claim_service.dart';
import '../domain/claim.dart';

class InMemoryClaimService implements ClaimService {
  final List<Claim> _claims = [];

  List<Claim> get claims => List.unmodifiable(_claims);

  @override
  Future<Claim> requestClaim({
    required String objectId,
    required String userId,
    required bool identityVerified,
  }) async {
    if (!identityVerified) {
      throw StateError('La reclamación requiere verificación de identidad.');
    }

    final claim = Claim(
      objectId: objectId,
      userId: userId,
      verified: true,
    );
    _claims.add(claim);
    return claim;
  }
}
