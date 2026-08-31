import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as path;

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
      for (final layer in [
        'domain',
        'application',
        'infrastructure',
        'public',
      ]) {
        expect(
          Directory('lib/features/$module/$layer').existsSync(),
          isTrue,
          reason: 'Falta lib/features/$module/$layer',
        );
      }
    }

    expect(Directory('lib/core/public').existsSync(), isTrue);
    expect(File('docs/c4/contexto.mmd').existsSync(), isTrue);
    expect(File('docs/adr/0001-estilo-arquitectonico.md').existsSync(), isTrue);
  });

  test('un módulo solo importa public/ de otro módulo', () {
    final featureRoot = Directory('lib/features');
    final violations = <String>[];
    final importPattern = RegExp("import\\s+['\"]([^'\"]+)['\"];");

    for (final entity in featureRoot.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;

      final relativeFile = path.normalize(entity.path);
      final parts = path.split(relativeFile);
      final featuresIndex = parts.indexOf('features');
      if (featuresIndex == -1 || featuresIndex + 1 >= parts.length) continue;
      final sourceModule = parts[featuresIndex + 1];

      final source = entity.readAsStringSync();
      for (final match in importPattern.allMatches(source)) {
        final importValue = match.group(1)!;
        String? targetPath;

        if (importValue.startsWith('package:lostvault/')) {
          targetPath = path.normalize(
            path.join('lib', importValue.substring('package:lostvault/'.length)),
          );
        } else if (importValue.startsWith('.')) {
          targetPath = path.normalize(
            path.join(path.dirname(relativeFile), importValue),
          );
        }

        if (targetPath == null) continue;

        final targetParts = path.split(targetPath);
        final targetFeaturesIndex = targetParts.indexOf('features');
        if (targetFeaturesIndex == -1 ||
            targetFeaturesIndex + 2 >= targetParts.length) {
          continue;
        }

        final targetModule = targetParts[targetFeaturesIndex + 1];
        final targetLayer = targetParts[targetFeaturesIndex + 2];

        if (sourceModule != targetModule && targetLayer != 'public') {
          violations.add('$relativeFile -> $importValue');
        }
      }
    }

    expect(
      violations,
      isEmpty,
      reason: 'Imports entre módulos fuera de public/:\n${violations.join('\n')}',
    );
  });
}
