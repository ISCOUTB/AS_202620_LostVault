import 'package:flutter/material.dart';
import 'package:lostvault/features/authentication/public/authentication.dart';
import 'composition.dart';
import 'pages/home_page.dart';
import 'pages/login_page.dart';
import 'pages/splash_page.dart';
import 'theme.dart';

class LostVaultApp extends StatefulWidget {
  const LostVaultApp({super.key});
  @override
  State<LostVaultApp> createState() => _LostVaultAppState();
}

class _LostVaultAppState extends State<LostVaultApp> {
  Session? _session;
  bool _booting = true;

  @override
  void initState() {
    super.initState();
    // La animación se muestra al menos 2.5 s, mientras se restaura la sesión.
    Future.wait([
      AppDependencies.instance.auth.restore(),
      Future<void>.delayed(const Duration(milliseconds: 2500)),
    ]).then((r) {
      if (mounted) setState(() { _session = r[0] as Session?; _booting = false; });
    });
  }

  Future<void> _logout() async {
    await AppDependencies.instance.auth.logout();
    if (mounted) setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Objetos Perdidos',
        debugShowCheckedModeBanner: false,
        theme: buildTheme(),
        home: AnimatedSwitcher(
          duration: const Duration(milliseconds: 400),
          child: _booting
              ? const SplashPage(key: ValueKey('splash'))
              : _session == null
                  ? LoginPage(
                      key: const ValueKey('login'),
                      onLoggedIn: (s) => setState(() => _session = s))
                  : HomePage(
                      key: ValueKey(_session!.email),
                      session: _session!,
                      onLogout: _logout),
        ),
      );
}
