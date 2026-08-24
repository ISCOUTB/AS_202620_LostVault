import 'package:flutter/material.dart';
import 'core/application/app_info.dart';
import 'core/public/app_shell.dart';
import 'features/objects/infrastructure/in_memory_object_service.dart';

void main() {
  runApp(const LostVaultApp());
}

class LostVaultApp extends StatelessWidget {
  const LostVaultApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppInfo.name,
      debugShowCheckedModeBanner: false,
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.deepPurple),
      home: const LostVaultHomePage(),
    );
  }
}

class LostVaultHomePage extends StatefulWidget {
  const LostVaultHomePage({super.key});

  @override
  State<LostVaultHomePage> createState() => _LostVaultHomePageState();
}

class _LostVaultHomePageState extends State<LostVaultHomePage> {
  final InMemoryObjectService _objects = InMemoryObjectService();

  Future<void> _publishDemoObject() async {
    await _objects.publish(title: 'Objeto encontrado', description: 'Publicación de ejemplo para validar el flujo modular.');
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return AppShell(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Marketplace de objetos perdidos', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            const Text('Esqueleto modular preparado para las funcionalidades de LostVault.'),
            const SizedBox(height: 24),
            FilledButton.icon(onPressed: _publishDemoObject, icon: const Icon(Icons.add), label: const Text('Publicar objeto de ejemplo')),
            const SizedBox(height: 16),
            Text('Objetos publicados: ${_objects.objects.length}'),
            for (final object in _objects.objects) ListTile(title: Text(object.title), subtitle: Text(object.description)),
          ],
        ),
      ),
    );
  }
}
