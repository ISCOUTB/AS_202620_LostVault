import '../domain/claim.dart';

abstract class ClaimService {
  Future<Claim> claim(String objectId, {required String idempotencyKey});
}
