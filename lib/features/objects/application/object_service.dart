import '../domain/lost_object.dart';

abstract interface class ObjectService {
  List<LostObject> get objects;

  Future<LostObject?> findById(String id);

  Future<LostObject> publish({
    required String title,
    required String description,
  });

  Future<LostObject> markAsClaimed(String id);
}
