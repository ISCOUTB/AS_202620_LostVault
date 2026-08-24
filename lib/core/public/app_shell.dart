import 'package:flutter/material.dart';
import '../application/app_info.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(AppInfo.name)),
      body: child,
    );
  }
}
