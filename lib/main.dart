import 'package:flutter/material.dart';
import 'app/app.dart';
import 'app/composition.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  AppDependencies.init();
  runApp(const LostVaultApp());
}
