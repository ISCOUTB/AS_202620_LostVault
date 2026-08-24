import '../../objects/public/objects.dart';
import '../application/search_service.dart';
import '../domain/search_result.dart';

class InMemorySearchService implements SearchService {
  InMemorySearchService(this.objects);
  final List<LostObject> objects;

  @override
  Future<SearchResult> search(String query) async {
    final q = query.trim().toLowerCase();
    return SearchResult(objects.where((o) => o.title.toLowerCase().contains(q) || o.description.toLowerCase().contains(q)).toList());
  }
}
