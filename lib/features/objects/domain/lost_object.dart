enum LostObjectStatus { available, claimed }

class LostObject {
  const LostObject({
    required this.id,
    required this.title,
    required this.description,
    this.status = LostObjectStatus.available,
  });

  final String id;
  final String title;
  final String description;
  final LostObjectStatus status;

  bool get isAvailable => status == LostObjectStatus.available;

  LostObject markAsClaimed() => LostObject(
        id: id,
        title: title,
        description: description,
        status: LostObjectStatus.claimed,
      );
}
