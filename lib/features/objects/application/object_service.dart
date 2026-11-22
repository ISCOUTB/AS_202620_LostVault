import '../domain/lost_object.dart';

abstract class ObjectService {
  Future<ObjectListing> list();
  Future<void> create(ObjectDraft draft);
  Future<void> delete(String objectId);
  Future<void> markClaimed(String objectId);
}
