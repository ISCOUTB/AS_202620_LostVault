import '../application/user_service.dart';
import '../domain/user_profile.dart';

class InMemoryUserService implements UserService {
  @override
  Future<UserProfile?> findById(String id) async => id.isEmpty ? null : UserProfile(id: id, displayName: id);
}
