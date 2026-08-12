import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/app_controller.dart';
import 'package:zenit_mobile/domain/mowing_demo_lifecycle.dart';
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

  testWidgets('captures three guarded post-service mowing heights', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1200, 2400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final plan = preparedMowingPlan();
    final vault = MemoryVault()
      ..mowingLifecycleEvents[plan.id] = [
        MowingDemoLifecycleEvent(
          eventId: '10000000-0000-4000-8000-000000000001',
          mowingOrderId: plan.id,
          sourcePlanningApprovalId: plan.planningApprovalId!,
          operation: MowingDemoOperation.confirm,
          occurredAt: DateTime.utc(2026, 8, 12, 13),
        ),
        MowingDemoLifecycleEvent(
          eventId: '10000000-0000-4000-8000-000000000002',
          mowingOrderId: plan.id,
          sourcePlanningApprovalId: plan.planningApprovalId!,
          operation: MowingDemoOperation.start,
          occurredAt: DateTime.utc(2026, 8, 12, 13),
          simulatedLatitude: preparedOrder().points.first.latitude,
          simulatedLongitude: preparedOrder().points.first.longitude,
        ),
        MowingDemoLifecycleEvent(
          eventId: '10000000-0000-4000-8000-000000000003',
          mowingOrderId: plan.id,
          sourcePlanningApprovalId: plan.planningApprovalId!,
          operation: MowingDemoOperation.finish,
          occurredAt: DateTime.utc(2026, 8, 12, 13),
        ),
      ];
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [preparedOrder()], mowingPlans: [plan]),
      sessionStore: MemorySessionStore()..value = validSession(),
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
      clock: () => DateTime.utc(2026, 8, 12, 14),
    );
    await controller.initialize();

    await tester.pumpWidget(ZenitApp(controller: controller));
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('NÃO EXECUTÁVEL'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Medições pós-serviço simuladas'),
      400,
      scrollable: find.byType(Scrollable).last,
    );

    expect(find.byType(TextField), findsNWidgets(3));
    expect(find.textContaining('não embute GPS ou foto'), findsOneWidget);
    await tester.enterText(find.byType(TextField).at(0), '5');
    await tester.enterText(find.byType(TextField).at(1), '6,5');
    await tester.enterText(find.byType(TextField).at(2), '8');
    await tester.scrollUntilVisible(
      find.text('Salvar 3 medições simuladas'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.text('Salvar 3 medições simuladas'));
    await tester.pumpAndSettle();

    final measurements = await vault.readMowingPostServiceMeasurements(plan.id);
    expect(measurements.map((item) => item.heightCm), [5, 6.5, 8]);
    expect(
      find.textContaining('foram criptografadas no aparelho'),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(
      find.text('Fotos pós-serviço simuladas'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    expect(find.text('Capturar'), findsNWidgets(3));
    await tester.tap(find.text('Capturar').first);
    await tester.pumpAndSettle();
    expect(await vault.readMowingPostServicePhotos(plan.id), hasLength(1));
    expect(find.textContaining('conteúdo não enviado'), findsWidgets);
  });
}
