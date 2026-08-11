import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/app_controller.dart';
import 'package:zenit_mobile/main.dart';

import 'support/fakes.dart';

void main() {
  testWidgets('shows guarded initial online login', (tester) async {
    final controller = ZenitAppController(
      gateway: FakeGateway(),
      sessionStore: MemorySessionStore(),
      vault: MemoryVault(),
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
    );
    await controller.initialize();

    await tester.pumpWidget(ZenitApp(controller: controller));

    expect(find.text('ZENIT Campo'), findsOneWidget);
    expect(
      find.text('Acesso inicial on-line. A senha nunca é armazenada.'),
      findsOneWidget,
    );
    expect(find.byType(TextField), findsNWidgets(2));
  });

  testWidgets('shows mowing planning as read-only and non-executable', (
    tester,
  ) async {
    final controller = ZenitAppController(
      gateway: FakeGateway(mowingPlans: [preparedMowingPlan()]),
      sessionStore: MemorySessionStore()..value = validSession(),
      vault: MemoryVault(),
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
    );
    await controller.initialize();

    await tester.pumpWidget(ZenitApp(controller: controller));
    await tester.pumpAndSettle();

    expect(find.text('Planejamentos de roçada — demonstração'), findsOneWidget);
    expect(find.textContaining('NÃO EXECUTÁVEL'), findsOneWidget);
    await tester.tap(find.textContaining('NÃO EXECUTÁVEL'));
    await tester.pumpAndSettle();

    expect(find.text('DEMONSTRAÇÃO — NÃO EXECUTÁVEL'), findsOneWidget);
    expect(
      find.textContaining(
        'Confirmar, iniciar, rastrear e concluir permanecem bloqueados.',
      ),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.text('Não satisfeita'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    expect(find.text('Não satisfeita'), findsOneWidget);
    expect(find.byType(FilledButton), findsNothing);
  });
}
