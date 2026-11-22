import 'package:lostvault/features/objects/public/objects.dart';

class SearchObjectsUseCase {
  SearchObjectsUseCase(this._objects);
  final ObjectService _objects;

  Future<ObjectListing> call({String query = ''}) async {
    final all = await _objects.list();
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return all;
    return ObjectListing(all.items
        .where((o) =>
            o.name.toLowerCase().contains(q) ||
            o.location.toLowerCase().contains(q) ||
            o.description.toLowerCase().contains(q))
        .toList());
  }
}
