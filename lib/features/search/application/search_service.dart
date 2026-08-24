import '../domain/search_result.dart';

abstract interface class SearchService {
  Future<SearchResult> search(String query);
}
