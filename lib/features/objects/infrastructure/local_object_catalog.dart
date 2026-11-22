import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../domain/lost_object.dart';

/// Catálogo local: la API no expone un endpoint para listar objetos,
/// así que se guardan aquí los que el usuario reporta (por cuenta).
class LocalObjectCatalog {
  LocalObjectCatalog(this._owner);
  final String Function() _owner;

  String get _key => 'objects_${_owner()}';

  Future<List<LostObject>> load() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString(_key);
    if (raw == null) return [];
    try {
      return [
        for (final e in jsonDecode(raw) as List)
          _fromMap(Map<String, dynamic>.from(e as Map)),
      ];
    } catch (_) {
      return [];
    }
  }

  Future<void> save(List<LostObject> items) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_key, jsonEncode(items.map(_toMap).toList()));
  }

  Map<String, dynamic> _toMap(LostObject o) => {
        'id': o.id,
        'name': o.name,
        'description': o.description,
        'location': o.location,
        'foundDate': o.foundDate,
        'imagePath': o.imagePath,
        'claimed': !o.isAvailable,
      };

  LostObject _fromMap(Map<String, dynamic> m) => LostObject(
        id: '${m['id']}',
        name: '${m['name']}',
        description: '${m['description'] ?? ''}',
        location: '${m['location'] ?? ''}',
        foundDate: '${m['foundDate'] ?? ''}',
        imagePath: m['imagePath'] as String?,
        status: m['claimed'] == true ? ObjectStatus.claimed : ObjectStatus.available,
      );
}
