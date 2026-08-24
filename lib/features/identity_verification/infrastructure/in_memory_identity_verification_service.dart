import '../application/identity_verification_service.dart';
import '../domain/verification.dart';

class InMemoryIdentityVerificationService implements IdentityVerificationService {
  @override
  Future<Verification> verify(String userId) async => Verification(userId: userId, valid: userId.isNotEmpty);
}
