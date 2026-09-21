import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:yaml/yaml.dart';

void main() {
  late YamlMap document;
  late YamlMap operation;

  setUpAll(() {
    document = loadYaml(
      File('docs/contracts/lostvault-api.yaml').readAsStringSync(),
    ) as YamlMap;
    operation = ((document['paths'] as YamlMap)[
        '/v1/objects/{objectId}/claims'] as YamlMap)['post'] as YamlMap;
  });

  test('declares a versioned OpenAPI 3.1 contract', () {
    expect(document['openapi'], startsWith('3.1.'));
    expect((document['info'] as YamlMap)['version'], '1.0.0');
  });

  test('consumer can create a claim only through the agreed protected route', () {
    expect(operation['operationId'], 'createClaim');
    expect(operation['security'], isNotEmpty);

    final parameters = operation['parameters'] as YamlList;
    final objectId = parameters.singleWhere(
      (parameter) => (parameter as YamlMap)['name'] == 'objectId',
    ) as YamlMap;
    expect(objectId['in'], 'path');
    expect(objectId['required'], true);
    expect((objectId['schema'] as YamlMap)['type'], 'string');
  });

  test('consumer receives the verified claim fields it depends on', () {
    final claim = (((document['components'] as YamlMap)['schemas'] as YamlMap)[
        'Claim'] as YamlMap);
    expect(claim['required'], containsAll(<String>['objectId', 'userId', 'verified']));

    final properties = claim['properties'] as YamlMap;
    expect((properties['objectId'] as YamlMap)['type'], 'string');
    expect((properties['userId'] as YamlMap)['type'], 'string');
    expect((properties['verified'] as YamlMap)['type'], 'boolean');
    expect((properties['verified'] as YamlMap)['const'], true);
  });

  test('consumer can distinguish every failure mode of the claim flow', () {
    final responses = operation['responses'] as YamlMap;
    expect(responses.keys, containsAll(<String>['201', '401', '404', '409', '422']));
  });
}
