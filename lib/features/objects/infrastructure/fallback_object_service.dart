import 'package:lostvault/core/public/core.dart';
import '../application/object_service.dart';
import '../domain/lost_object.dart';

/// Usa la API; si el listado no existe o falla, muestra datos de ejemplo.
class FallbackObjectService implements ObjectService {
  FallbackObjectService(this._remote, this._demo);
  final ObjectService _remote;
  final ObjectService _demo;

  @override
  Future<ObjectListing> list() async {
    try {
      return await _remote.list();
    } on Failure catch (f) {
      if (f.code == 'UNAUTHENTICATED') rethrow;
      return _demo.list();
    }
  }

  @override
  Future<void> create(ObjectDraft draft) => _remote.create(draft);

  @override
  Future<void> delete(String objectId) => _remote.delete(objectId);
}
