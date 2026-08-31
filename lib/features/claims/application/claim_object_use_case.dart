import '../../../core/public/core.dart';
import '../../authentication/public/authentication.dart';
import '../../identity_verification/public/identity_verification.dart';
import '../../objects/public/objects.dart';
import '../domain/claim.dart';
import 'claim_service.dart';

class ClaimObjectUseCase {
  ClaimObjectUseCase({
    required AuthenticationService authentication,
    required IdentityVerificationService identityVerification,
    required ObjectService objects,
    required ClaimService claims,
  })  : _authentication = authentication,
        _identityVerification = identityVerification,
        _objects = objects,
        _claims = claims;

  final AuthenticationService _authentication;
  final IdentityVerificationService _identityVerification;
  final ObjectService _objects;
  final ClaimService _claims;

  Future<Result<Claim>> execute(String objectId) async {
    final user = _authentication.currentUser;
    if (user == null) {
      return Result.failure(
        'Reclamación bloqueada: debes iniciar sesión.',
      );
    }

    final object = await _objects.findById(objectId);
    if (object == null) {
      return Result.failure('Reclamación bloqueada: el objeto no existe.');
    }

    if (!object.isAvailable) {
      return Result.failure('Reclamación bloqueada: el objeto ya fue reclamado.');
    }

    final verification = await _identityVerification.verify(user.id);
    if (!verification.valid) {
      return Result.failure(
        'Reclamación bloqueada: la identidad no pudo verificarse.',
      );
    }

    try {
      final claim = await _claims.requestClaim(
        objectId: object.id,
        userId: user.id,
        identityVerified: verification.valid,
      );
      await _objects.markAsClaimed(object.id);
      return Result.success(claim);
    } on StateError catch (error) {
      return Result.failure('Reclamación bloqueada: ${error.message}');
    }
  }
}
