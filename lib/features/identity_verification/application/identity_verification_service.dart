import '../domain/verification.dart';

abstract interface class IdentityVerificationService {
  Future<Verification> verify(String userId);
}
