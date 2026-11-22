import '../application/object_service.dart';
import '../domain/lost_object.dart';

/// Adaptador en memoria (mismo patrón que el corte vertical del repo).
class InMemoryObjectService implements ObjectService {
  InMemoryObjectService()
      : _items = [
          const LostObject(
              id: 'demo-1', name: 'Llaves con llavero de la U',
              description: '', location: 'Biblioteca Bloque B', foundDate: '2026-05-18'),
          const LostObject(
              id: 'demo-2', name: 'Mochila negra Nike',
              description: '', location: 'Biblioteca Bloque B', foundDate: '2026-05-18'),
          const LostObject(
              id: 'demo-3', name: 'Botella Hydro Flask',
              description: '', location: 'Biblioteca Bloque B', foundDate: '2026-05-18'),
          const LostObject(
              id: 'demo-4', name: 'Botella Hydro Flask',
              description: '', location: 'Biblioteca Bloque B', foundDate: '2026-05-18'),
        ];

  final List<LostObject> _items;

  @override
  Future<ObjectListing> list() async =>
      ObjectListing(List.unmodifiable(_items), fromDemo: true);

  @override
  Future<void> create(ObjectDraft d) async {
    _items.insert(
        0,
        LostObject(
            id: 'local-${DateTime.now().millisecondsSinceEpoch}',
            name: d.name,
            description: d.description,
            location: d.location,
            foundDate: d.foundDate));
  }

  @override
  Future<void> delete(String objectId) async =>
      _items.removeWhere((o) => o.id == objectId);
}
