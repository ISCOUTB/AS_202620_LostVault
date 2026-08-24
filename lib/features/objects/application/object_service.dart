import '../domain/lost_object.dart';

abstract interface class ObjectService {
  Future<LostObject> publish({required String title, required String description});
}
