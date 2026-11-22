import 'package:lostvault/core/public/core.dart';
import '../application/object_service.dart';
import '../domain/lost_object.dart';

LostObject lostObjectFromJson(Map<String, dynamic> j) {
  final status = '${j['status'] ?? ''}'.toUpperCase();
  final claimed = j['claimed'] == true ||
      status.contains('CLAIM') ||
      status.contains('RECLAM');
  return LostObject(
    id: '${j['id'] ?? j['objectId'] ?? ''}',
    name: '${j['name'] ?? j['title'] ?? 'Sin nombre'}',
    description: '${j['description'] ?? ''}',
    location: '${j['location'] ?? ''}',
    foundDate:
        '${j['foundDate'] ?? j['found_at'] ?? j['createdAt'] ?? ''}'.split('T').first,
    imageUrl: (j['imageUrl'] ?? j['image_url'] ?? j['image']) as String?,
    status: claimed ? ObjectStatus.claimed : ObjectStatus.available,
  );
}

class HttpObjectService implements ObjectService {
  HttpObjectService(this._api);
  final ApiClient _api;

  // GET /v1/objects  (ASUMIDO: no aparece en el /docs actual)
  @override
  Future<ObjectListing> list() async {
    final res = await _api.get('/v1/objects');
    final raw = res is List ? res : (res is Map ? (res['items'] ?? res['data'] ?? []) : []);
    return ObjectListing([
      for (final e in raw as List)
        lostObjectFromJson(Map<String, dynamic>.from(e as Map)),
    ]);
  }

  // POST /v1/objects  (ASUMIDO: campos name, description, location, foundDate, imageBase64)
  @override
  Future<void> create(ObjectDraft d) => _api.post('/v1/objects', body: {
        'name': d.name,
        'description': d.description,
        'location': d.location,
        'foundDate': d.foundDate,
        if (d.imageBase64 != null) 'imageBase64': d.imageBase64,
      });

  // DELETE /v1/objects/{objectId}
  @override
  Future<void> delete(String objectId) => _api.delete('/v1/objects/$objectId');
}
