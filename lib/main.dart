import 'package:flutter/material.dart';

import 'core/application/app_info.dart';
import 'core/public/app_shell.dart';
import 'features/authentication/infrastructure/in_memory_authentication_service.dart';
import 'features/claims/application/claim_object_use_case.dart';
import 'features/claims/infrastructure/in_memory_claim_service.dart';
import 'features/identity_verification/infrastructure/in_memory_identity_verification_service.dart';
import 'features/objects/domain/lost_object.dart';
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
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.deepPurple,
      ),
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
  late final InMemoryAuthenticationService _authentication;
  late final InMemoryObjectService _objects;
  late final ClaimObjectUseCase _claimObject;

  String _feedback =
      'Prueba el corte vertical: primero intenta reclamar sin iniciar sesión.';

  @override
  void initState() {
    super.initState();

    _authentication = InMemoryAuthenticationService();
    _objects = InMemoryObjectService(
      seed: const [
        LostObject(
          id: 'obj-001',
          title: 'Termo negro',
          description: 'Encontrado cerca de la biblioteca.',
        ),
      ],
    );

    _claimObject = ClaimObjectUseCase(
      authentication: _authentication,
      identityVerification: const InMemoryIdentityVerificationService(),
      objects: _objects,
      claims: InMemoryClaimService(),
    );
  }

  Future<void> _signIn() async {
    final user = await _authentication.signIn('estudiante@utb.edu.co');
    if (!mounted) return;

    setState(() {
      _feedback = user == null
          ? 'No fue posible iniciar sesión.'
          : 'Sesión iniciada como ${user.email}.';
    });
  }

  Future<void> _claim(String objectId) async {
    final result = await _claimObject.execute(objectId);
    if (!mounted) return;

    setState(() {
      _feedback = result.isSuccess
          ? 'Reclamación autorizada: identidad verificada y objeto marcado como reclamado.'
          : result.error!;
    });
  }

  @override
  Widget build(BuildContext context) {
    final object = _objects.objects.first;
    final session = _authentication.currentUser;

    return AppShell(
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            'Corte vertical ejecutable — AS-03 Seguridad',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          const Text(
            'Flujo: interfaz → autenticación → verificación de identidad → reclamación → actualización del objeto.',
          ),
          const SizedBox(height: 24),
          Card(
            child: ListTile(
              leading: const Icon(Icons.inventory_2_outlined),
              title: Text(object.title),
              subtitle: Text(object.description),
              trailing: Chip(
                label: Text(object.isAvailable ? 'Disponible' : 'Reclamado'),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            session == null
                ? 'Sesión: no autenticado'
                : 'Sesión: ${session.email}',
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              OutlinedButton.icon(
                onPressed: session == null ? _signIn : null,
                icon: const Icon(Icons.login),
                label: const Text('Iniciar sesión de prueba'),
              ),
              FilledButton.icon(
                onPressed: () => _claim(object.id),
                icon: const Icon(Icons.verified_user_outlined),
                label: const Text('Reclamar objeto'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Semantics(
            liveRegion: true,
            child: Text(
              _feedback,
              key: const Key('claim-feedback'),
              style: Theme.of(context).textTheme.bodyLarge,
            ),
          ),
        ],
      ),
    );
  }
}
