enum ObjectStatus { available, claimed }

class LostObject {
  const LostObject({
    required this.id,
    required this.name,
    required this.description,
    required this.location,
    required this.foundDate,
    this.imagePath,
    this.status = ObjectStatus.available,
  });

  final String id;
  final String name;
  final String description;
  final String location;
  final String foundDate; // yyyy-MM-dd
  final String? imagePath; // foto local del dispositivo
  final ObjectStatus status;

  bool get isAvailable => status == ObjectStatus.available;

  LostObject copyWith({ObjectStatus? status}) => LostObject(
        id: id,
        name: name,
        description: description,
        location: location,
        foundDate: foundDate,
        imagePath: imagePath,
        status: status ?? this.status,
      );
}

/// Datos para registrar un objeto.
/// La API solo recibe name y description; ubicación, fecha y foto se guardan en el dispositivo.
class ObjectDraft {
  const ObjectDraft({
    required this.name,
    required this.description,
    required this.location,
    required this.foundDate,
    this.imagePath,
  });

  final String name;
  final String description;
  final String location;
  final String foundDate;
  final String? imagePath;
}

class ObjectListing {
  const ObjectListing(this.items);
  final List<LostObject> items;
}
