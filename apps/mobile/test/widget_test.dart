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

  testWidgets('shows a clearly simulated non-operational mowing rehearsal', (
    tester,
  ) async {
    final controller = ZenitAppController(
      gateway: FakeGateway(
        orders: [preparedOrder()],
        mowingPlans: [preparedMowingPlan()],
      ),
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

    expect(find.text('ENSAIO SIMULADO — NÃO É EXECUÇÃO'), findsOneWidget);
    expect(
      find.textContaining(
        'Não há despacho, GPS real, rastreamento, serviço de campo',
      ),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.text('1. Confirmar ensaio'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    expect(find.text('1. Confirmar ensaio'), findsOneWidget);
    expect(find.text('2. Iniciar (ponto simulado)'), findsOneWidget);
    expect(find.text('Pausar ensaio'), findsOneWidget);
    expect(find.text('Retomar ensaio'), findsOneWidget);
    expect(find.text('3. Finalizar ensaio'), findsOneWidget);
    expect(find.byType(FilledButton), findsNothing);
  });
}
