import 'package:lostvault/core/public/core.dart';
import '../application/object_service.dart';
import '../infrastructure/api_object_service.dart';
import '../infrastructure/local_object_catalog.dart';

export '../application/object_service.dart';
export '../domain/lost_object.dart';

ObjectService createObjectService(ApiClient api, TokenStore store) =>
    ApiObjectService(api, LocalObjectCatalog(() => store.email ?? 'anon'));
