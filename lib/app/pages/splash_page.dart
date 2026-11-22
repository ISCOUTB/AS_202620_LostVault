import 'dart:async';
import 'package:flutter/material.dart';
import '../theme.dart';

/// Pantalla de carga: fondo azul, logo blanco y puntos animados.
class SplashPage extends StatefulWidget {
  const SplashPage({super.key});
  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> {
  late final Timer _timer;
  bool _first = true;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (mounted) setState(() => _first = !_first);
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  Widget _dot(bool active) => AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
        margin: const EdgeInsets.symmetric(horizontal: 5),
        width: active ? 14 : 8,
        height: active ? 14 : 8,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: active ? Colors.white : Colors.white54,
        ),
      );

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: kSplash,
        body: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Image.asset(
              'assets/images/logo_utb_blanco.png',
              width: 200,
              errorBuilder: (_, __, ___) => Image.asset(
                'assets/images/logo_utb.png',
                width: 200,
                color: Colors.white,
                errorBuilder: (_, __, ___) => const Text('UTB',
                    style: TextStyle(
                        color: Colors.white, fontSize: 56, fontWeight: FontWeight.bold)),
              ),
            ),
            const SizedBox(height: 28),
            Row(mainAxisSize: MainAxisSize.min, children: [_dot(_first), _dot(!_first)]),
          ]),
        ),
      );
}
