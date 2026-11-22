import 'package:lostvault/core/public/core.dart';
import '../application/claim_object_use_case.dart';
import '../infrastructure/http_claim_service.dart';

export '../application/claim_object_use_case.dart';
export '../domain/claim.dart';

ClaimObjectUseCase createClaimObjectUseCase(ApiClient api) =>
    ClaimObjectUseCase(HttpClaimService(api));
