import 'package:lostvault/core/public/core.dart';
import '../application/object_service.dart';
import '../domain/lost_object.dart';
import 'local_object_catalog.dart';

class ApiObjectService implements ObjectService {
  ApiObjectService(this._api, this._catalog);
  final ApiClient _api;
  final LocalObjectCatalog _catalog;

  @override
  Future<ObjectListing> list() async => ObjectListing(await _catalog.load());

  // POST /v1/objects  -> solo {name, description}; responde 201 {id, name, ...}
  @override
  Future<void> create(ObjectDraft d) async {
    final res = await _api.post('/v1/objects', body: {
      'name': d.name,
      if (d.description.isNotEmpty) 'description': d.description,
    });
    final id = res is Map ? res['id'] : null;
    if (id == null) {
      throw const Failure('INVALID_RESPONSE', 'La API no devolvió el id del objeto.');
    }
    final items = await _catalog.load();
    items.insert(
      0,
      LostObject(
        id: '$id',
        name: d.name,
        description: d.description,
        location: d.location,
        foundDate: d.foundDate,
        imagePath: d.imagePath,
      ),
    );
    await _catalog.save(items);
  }

  // DELETE /v1/objects/{id} -> 204. 403 = no es tuyo, 409 = ya reclamado.
  @override
  Future<void> delete(String objectId) async {
    try {
      await _api.delete('/v1/objects/$objectId');
    } on Failure catch (f) {
      // 404: ya no existe en el servidor (p. ej. se reinició); lo quitamos localmente.
      if (f.statusCode != 404) rethrow;
    }
    final items = await _catalog.load();
    items.removeWhere((o) => o.id == objectId);
    await _catalog.save(items);
  }

  @override
  Future<void> markClaimed(String objectId) async {
    final items = await _catalog.load();
    final i = items.indexWhere((o) => o.id == objectId);
    if (i < 0) return;
    items[i] = items[i].copyWith(status: ObjectStatus.claimed);
    await _catalog.save(items);
  }
}
