import '../domain/claim.dart';

abstract interface class ClaimService {
  Future<Claim> requestClaim({required String objectId, required String userId, required bool identityVerified});
}
