import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/app/zenit_app.dart';
import 'package:zenit_mobile/app_controller.dart';
import 'package:zenit_mobile/domain/measurement_draft.dart';
import 'package:zenit_mobile/features/inspection/presentation/order_draft_page.dart';

import 'support/fakes.dart';

void main() {
  testWidgets(
    'order collection journey guides the user through each step and preserves drafts across reloads',
    (tester) async {
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final order = preparedOrder();
      final vault = MemoryVault();
      final gateway = FakeGateway(orders: [order]);
      final controller = ZenitAppController(
        gateway: gateway,
        sessionStore: MemorySessionStore()..value = validSession(),
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        photoCapture: FakePhotoCapture(),
        appVersion: 'test',
        clock: () => DateTime.utc(2026, 8, 12, 14),
      );
      await controller.initialize();

      // 1. Open app and view inbox
      await tester.pumpWidget(ZenitApp(controller: controller));
      await tester.pumpAndSettle();

      expect(find.text('Inspeções preparadas'), findsOneWidget);
      expect(
        find.textContaining(
          '${order.roadCode} · segmento ${order.segmentIndex}',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('somente rascunho local'), findsOneWidget);

      // Open the order
      await tester.tap(
        find.textContaining(
          '${order.roadCode} · segmento ${order.segmentIndex}',
        ),
      );
      await tester.pumpAndSettle();

      // 2. Initial state: user is clearly guided to the next action (Step 1: Confirm)
      expect(find.text('PRÓXIMO PASSO DA JORNADA'), findsOneWidget);
      expect(
        find.textContaining('Passo 1: Toque em "1. Confirmar"'),
        findsOneWidget,
      );

      // Tap Step 1: Confirm
      await tester.tap(find.text('1. Confirmar'));
      await tester.pumpAndSettle();

      // 3. Next action guides to Step 2: Start
      expect(
        find.textContaining('Passo 2: Toque em "2. Iniciar (GPS simulado)"'),
        findsOneWidget,
      );

      // Tap Step 2: Iniciar
      await tester.tap(find.text('2. Iniciar (GPS simulado)'));
      await tester.pumpAndSettle();

      expect(find.textContaining('GPS simulado:'), findsOneWidget);
      expect(
        find.textContaining('Passo 3: Digite as alturas dos 3 pontos'),
        findsOneWidget,
      );

      // 4. Enter heights for all 3 points
      await tester.enterText(find.byType(TextField).at(0), '8.5');
      await tester.enterText(find.byType(TextField).at(1), '14.0');
      await tester.enterText(find.byType(TextField).at(2), '32.0');
      await tester.pumpAndSettle();

      // Dynamic vegetation tier badges appear
      expect(find.textContaining('N1 < 10 cm'), findsOneWidget);
      expect(find.textContaining('N2 10-30 cm'), findsOneWidget);
      expect(find.textContaining('N3 > 30 cm'), findsOneWidget);

      // 5. Save drafts locally in device vault
      await tester.scrollUntilVisible(
        find.text('Salvar 3 rascunhos no aparelho'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(find.text('Salvar 3 rascunhos no aparelho'));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Três eventos preparados e criptografados'),
        findsOneWidget,
      );

      // 6. Test acceptance criterion: "fechar/reabrir não perde rascunho"
      // Simulate closing and reopening the page
      await tester.pumpWidget(
        MaterialApp(
          home: OrderDraftPage(controller: controller, order: order),
        ),
      );
      await tester.pumpAndSettle();

      // Verify that all 3 heights are reloaded from the encrypted vault intact!
      expect(find.widgetWithText(TextField, '8.5'), findsOneWidget);
      expect(find.widgetWithText(TextField, '14.0'), findsOneWidget);
      expect(find.widgetWithText(TextField, '32.0'), findsOneWidget);
      expect(find.textContaining('N1 < 10 cm'), findsOneWidget);
      expect(find.textContaining('N2 10-30 cm'), findsOneWidget);
      expect(find.textContaining('N3 > 30 cm'), findsOneWidget);

      // 7. Capture photos for all 3 points
      for (var i = 0; i < 3; i++) {
        final captureButton = find.text(
          'Capturar foto preparada do ponto ${i + 1}',
        );
        await tester.scrollUntilVisible(
          captureButton,
          200,
          scrollable: find.byType(Scrollable).first,
        );
        await tester.tap(captureButton);
        await tester.pumpAndSettle();
      }

      // 8. Next step guides user to finalize
      expect(
        find.textContaining('Passo 4: Toque em "3. Finalizar"'),
        findsOneWidget,
      );

      // Scroll up to the lifecycle action buttons
      await tester.drag(find.byType(Scrollable).first, const Offset(0, 1500));
      await tester.pumpAndSettle();

      await tester.tap(find.text('3. Finalizar'));
      await tester.pumpAndSettle();

      // 9. Summary card appears displaying local vs remote state
      expect(find.text('Resumo da Coleta: Local vs Enviado'), findsOneWidget);
      expect(
        find.textContaining('Cofre local: 3/3 alturas e 3/3 fotos'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Passo 5: Toque em "Sincronizar lote preparado"'),
        findsOneWidget,
      );

      // 10. Sync prepared batch
      await tester.scrollUntilVisible(
        find.text('Sincronizar lote preparado'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(find.text('Sincronizar lote preparado'));
      await tester.pumpAndSettle();

      expect(
        find.textContaining(
          'Passo 6: Manifestos aceitos. Toque em "Enviar fotos preparadas"',
        ),
        findsOneWidget,
      );

      // 11. Upload prepared photos
      await tester.scrollUntilVisible(
        find.text('Enviar fotos preparadas'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(find.text('Enviar fotos preparadas'));
      await tester.pumpAndSettle();

      // Scroll up to view the updated next step card
      await tester.drag(find.byType(Scrollable).first, const Offset(0, 1500));
      await tester.pumpAndSettle();

      // 12. Final step completion
      expect(
        find.textContaining('Jornada concluída: eventos e fotos transmitidos'),
        findsOneWidget,
      );

      final storedDrafts = await vault.readDrafts(order.id);
      expect(
        storedDrafts.every((d) => d.syncState == DraftSyncState.acknowledged),
        isTrue,
      );
      final storedPhotos = await vault.readPhotoDrafts(order.id);
      expect(storedPhotos.every((p) => p.isUploaded), isTrue);
    },
  );

  testWidgets('point cards fit a compact viewport at 200% text scale', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

    final order = preparedOrder();
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [order]),
      sessionStore: MemorySessionStore()..value = validSession(),
      vault: MemoryVault(),
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      photoCapture: FakePhotoCapture(),
      appVersion: 'test',
      clock: () => DateTime.utc(2026, 8, 12, 14),
    );
    await controller.initialize();
    expect(await controller.confirmDemoOrder(order), isTrue);
    expect(await controller.startDemoOrder(order), isTrue);

    await tester.pumpWidget(
      MaterialApp(
        home: OrderDraftPage(controller: controller, order: order),
      ),
    );
    await tester.pumpAndSettle();

    final thirdField = find.byWidgetPredicate(
      (widget) =>
          widget is TextField &&
          widget.decoration?.labelText == 'Ponto 3 · altura (cm)',
    );
    await tester.scrollUntilVisible(
      thirdField,
      200,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    expect(thirdField, findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
