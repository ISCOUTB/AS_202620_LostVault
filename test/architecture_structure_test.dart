import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('cada módulo mantiene sus cuatro fronteras arquitectónicas', () {
    const modules = [
      'authentication',
      'objects',
      'search',
      'claims',
      'identity_verification',
      'users',
    ];

    for (final module in modules) {
      for (final layer in ['domain', 'application', 'infrastructure', 'public']) {
        expect(Directory('lib/features/$module/$layer').existsSync(), isTrue,
            reason: 'Falta lib/features/$module/$layer');
      }
    }

    expect(Directory('lib/core/public').existsSync(), isTrue);
    expect(File('docs/c4/contexto.mmd').existsSync(), isTrue);
    expect(File('docs/adr/0001-estilo-arquitectonico.md').existsSync(), isTrue);
  });
}
