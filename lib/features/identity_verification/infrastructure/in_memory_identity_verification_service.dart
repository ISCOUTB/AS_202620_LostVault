import '../application/identity_verification_service.dart';
import '../domain/verification.dart';

class InMemoryIdentityVerificationService
    implements IdentityVerificationService {
  const InMemoryIdentityVerificationService({this.allowVerification = true});

  final bool allowVerification;

  @override
  Future<Verification> verify(String userId) async => Verification(
        userId: userId,
        valid: allowVerification && userId.trim().isNotEmpty,
      );
}
