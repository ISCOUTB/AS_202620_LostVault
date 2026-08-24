import '../application/object_service.dart';
import '../domain/lost_object.dart';

class InMemoryObjectService implements ObjectService {
  final List<LostObject> _objects = [];

  List<LostObject> get objects => List.unmodifiable(_objects);

  @override
  Future<LostObject> publish({required String title, required String description}) async {
    final object = LostObject(id: '${_objects.length + 1}', title: title, description: description);
    _objects.add(object);
    return object;
  }
}
