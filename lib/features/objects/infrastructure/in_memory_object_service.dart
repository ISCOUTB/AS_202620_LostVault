import '../application/object_service.dart';
import '../domain/lost_object.dart';

class InMemoryObjectService implements ObjectService {
  InMemoryObjectService({List<LostObject> seed = const []})
      : _objects = List<LostObject>.from(seed);

  final List<LostObject> _objects;

  @override
  List<LostObject> get objects => List.unmodifiable(_objects);

  @override
  Future<LostObject?> findById(String id) async {
    for (final object in _objects) {
      if (object.id == id) return object;
    }
    return null;
  }

  @override
  Future<LostObject> publish({
    required String title,
    required String description,
  }) async {
    final object = LostObject(
      id: '${_objects.length + 1}',
      title: title,
      description: description,
    );
    _objects.add(object);
    return object;
  }

  @override
  Future<LostObject> markAsClaimed(String id) async {
    final index = _objects.indexWhere((object) => object.id == id);
    if (index == -1) {
      throw StateError('El objeto solicitado no existe.');
    }

    final current = _objects[index];
    if (!current.isAvailable) {
      throw StateError('El objeto ya fue reclamado.');
    }

    final updated = current.markAsClaimed();
    _objects[index] = updated;
    return updated;
  }
}
