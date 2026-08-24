import 'package:flutter_test/flutter_test.dart';
import 'package:lostvault/main.dart';

void main() {
  testWidgets('LostVault inicia correctamente', (tester) async {
    await tester.pumpWidget(const LostVaultApp());

    expect(find.text('LostVault — esqueleto ejecutable'), findsOneWidget);
  });
}
