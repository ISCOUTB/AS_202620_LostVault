import 'package:flutter_test/flutter_test.dart';
import 'package:lostvault/main.dart';

void main() {
  testWidgets('LostVault inicia correctamente', (tester) async {
    await tester.pumpWidget(const LostVaultApp());

    expect(find.text('Marketplace de objetos perdidos'), findsOneWidget);
    expect(find.text('Objetos publicados: 0'), findsOneWidget);
  });

  testWidgets('el flujo de publicación actualiza la interfaz', (tester) async {
    await tester.pumpWidget(const LostVaultApp());
    await tester.tap(find.text('Publicar objeto de ejemplo'));
    await tester.pump();

    expect(find.text('Objetos publicados: 1'), findsOneWidget);
    expect(find.text('Objeto encontrado'), findsOneWidget);
  });
}
