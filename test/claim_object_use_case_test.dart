import 'package:flutter_test/flutter_test.dart';
import 'package:lostvault/features/authentication/infrastructure/in_memory_authentication_service.dart';
import 'package:lostvault/features/claims/application/claim_object_use_case.dart';
import 'package:lostvault/features/claims/infrastructure/in_memory_claim_service.dart';
import 'package:lostvault/features/identity_verification/infrastructure/in_memory_identity_verification_service.dart';
import 'package:lostvault/features/objects/domain/lost_object.dart';
import 'package:lostvault/features/objects/infrastructure/in_memory_object_service.dart';

void main() {
  group('AS-03 Seguridad - ClaimObjectUseCase', () {
    test('bloquea una reclamación sin sesión autenticada', () async {
      final authentication = InMemoryAuthenticationService();
      final objects = InMemoryObjectService(
        seed: const [
          LostObject(id: '1', title: 'Termo', description: 'Negro'),
        ],
      );
      final useCase = ClaimObjectUseCase(
        authentication: authentication,
        identityVerification:
            const InMemoryIdentityVerificationService(),
        objects: objects,
        claims: InMemoryClaimService(),
      );

      final result = await useCase.execute('1');

      expect(result.isFailure, isTrue);
      expect(result.error, contains('iniciar sesión'));
      expect(objects.objects.single.isAvailable, isTrue);
    });

    test('bloquea una reclamación con identidad inválida', () async {
      final authentication = InMemoryAuthenticationService();
      await authentication.signIn('estudiante@utb.edu.co');
      final objects = InMemoryObjectService(
        seed: const [
          LostObject(id: '1', title: 'Termo', description: 'Negro'),
        ],
      );
      final claims = InMemoryClaimService();
      final useCase = ClaimObjectUseCase(
        authentication: authentication,
        identityVerification: const InMemoryIdentityVerificationService(
          allowVerification: false,
        ),
        objects: objects,
        claims: claims,
      );

      final result = await useCase.execute('1');

      expect(result.isFailure, isTrue);
      expect(result.error, contains('identidad'));
      expect(objects.objects.single.isAvailable, isTrue);
      expect(claims.claims, isEmpty);
    });

    test('autoriza la reclamación y marca el objeto como reclamado', () async {
      final authentication = InMemoryAuthenticationService();
      await authentication.signIn('estudiante@utb.edu.co');
      final objects = InMemoryObjectService(
        seed: const [
          LostObject(id: '1', title: 'Termo', description: 'Negro'),
        ],
      );
      final claims = InMemoryClaimService();
      final useCase = ClaimObjectUseCase(
        authentication: authentication,
        identityVerification:
            const InMemoryIdentityVerificationService(),
        objects: objects,
        claims: claims,
      );

      final result = await useCase.execute('1');

      expect(result.isSuccess, isTrue);
      expect(result.value?.verified, isTrue);
      expect(objects.objects.single.status, LostObjectStatus.claimed);
      expect(claims.claims, hasLength(1));
    });
  });
}
