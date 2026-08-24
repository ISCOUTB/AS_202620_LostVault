import '../domain/user_profile.dart';

abstract interface class UserService {
  Future<UserProfile?> findById(String id);
}
