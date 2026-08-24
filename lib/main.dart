import 'package:flutter/material.dart';

void main() {
  runApp(const LostVaultApp());
}

class LostVaultApp extends StatelessWidget {
  const LostVaultApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LostVault',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.deepPurple,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const Scaffold(
        body: Center(
          child: Text('LostVault — esqueleto ejecutable'),
        ),
      ),
    );
  }
}
