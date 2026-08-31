import 'package:flutter_test/flutter_test.dart';
import 'package:lostvault/main.dart';

void main() {
  testWidgets('el corte vertical inicia con objeto disponible', (tester) async {
    await tester.pumpWidget(const LostVaultApp());

    expect(
      find.text('Corte vertical ejecutable — AS-03 Seguridad'),
      findsOneWidget,
    );
    expect(find.text('Termo negro'), findsOneWidget);
    expect(find.text('Disponible'), findsOneWidget);
    expect(find.text('Sesión: no autenticado'), findsOneWidget);
  });

  testWidgets('bloquea reclamo sin autenticación', (tester) async {
    await tester.pumpWidget(const LostVaultApp());

    await tester.tap(find.text('Reclamar objeto'));
    await tester.pumpAndSettle();

    expect(
      find.text('Reclamación bloqueada: debes iniciar sesión.'),
      findsOneWidget,
    );
    expect(find.text('Disponible'), findsOneWidget);
  });

  testWidgets('flujo válido autentica, verifica y reclama', (tester) async {
    await tester.pumpWidget(const LostVaultApp());

    await tester.tap(find.text('Iniciar sesión de prueba'));
    await tester.pumpAndSettle();
    expect(find.text('Sesión: estudiante@utb.edu.co'), findsOneWidget);

    await tester.tap(find.text('Reclamar objeto'));
    await tester.pumpAndSettle();

    expect(find.text('Reclamado'), findsOneWidget);
    expect(
      find.text(
        'Reclamación autorizada: identidad verificada y objeto marcado como reclamado.',
      ),
      findsOneWidget,
    );
  });
}
