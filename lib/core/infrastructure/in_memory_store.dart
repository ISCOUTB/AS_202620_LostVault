class InMemoryStore<T> {
  final List<T> _items = [];

  List<T> get items => List.unmodifiable(_items);
  void add(T item) => _items.add(item);
  void clear() => _items.clear();
}
