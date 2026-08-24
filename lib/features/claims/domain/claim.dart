class Claim {
  const Claim({required this.objectId, required this.userId, this.verified = false});
  final String objectId;
  final String userId;
  final bool verified;
}
