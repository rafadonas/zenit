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
}
