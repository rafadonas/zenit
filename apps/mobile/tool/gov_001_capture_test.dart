// GOV-001 capture harness only: renders the unchanged application with test fakes.
// Run from apps/mobile; captures are ignored, synthetic and non-operational.
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/app_controller.dart';
import 'package:zenit_mobile/data/zenit_gateway.dart';
import 'package:zenit_mobile/domain/auth_session.dart';
import 'package:zenit_mobile/domain/mobile_sync.dart';
import 'package:zenit_mobile/main.dart';

import '../test/support/fakes.dart';

class CaptureGateway extends FakeGateway {
  Object? loginFailure;

  @override
  Future<AuthSession> login(String email, String password) async {
    if (loginFailure case final failure?) throw failure;
    return super.login(email, password);
  }
}

void main() {
  testWidgets('capture GOV-001 synthetic mobile inventory', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

    const outputPath = '../../data/processed/gov-001/mobile';
    final output = Directory(outputPath);
    final manifest = <Map<String, Object?>>[];
    final boundaryKey = GlobalKey();
    final fontPath =
        '../../.tools/flutter/engine/src/flutter/txt/third_party/fonts/Roboto-Regular.ttf';
    await tester.runAsync(() async {
      await output.create(recursive: true);
      final font = await File(fontPath).readAsBytes();
      for (final family in ['Roboto', 'Ahem']) {
        final loader = FontLoader(family)
          ..addFont(Future.value(ByteData.sublistView(font)));
        await loader.load();
      }
      final icons = FontLoader('MaterialIcons')
        ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
      await icons.load();
    });

    Future<void> mount(ZenitAppController controller) async {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpWidget(
        RepaintBoundary(
          key: boundaryKey,
          child: ZenitApp(controller: controller),
        ),
      );
      await tester.pump();
    }

    Future<void> show(Finder finder, {double scrollDelta = 260}) async {
      await tester.scrollUntilVisible(
        finder,
        scrollDelta,
        // The page-level ListView is the first Scrollable. Text fields and
        // buttons may add nested Scrollables with tiny viewports; selecting
        // the last one makes long, lazily built journeys impossible to reach.
        scrollable: find.byType(Scrollable).first,
        maxScrolls: 40,
      );
      await Scrollable.ensureVisible(tester.element(finder), alignment: 0.1);
      await tester.pumpAndSettle();
    }

    Future<void> capture(String name, String state) async {
      await tester.pump(const Duration(milliseconds: 100));
      final boundary =
          boundaryKey.currentContext!.findRenderObject()
              as RenderRepaintBoundary;
      final controls = <Map<String, Object?>>[];
      for (final element
          in find
              .byWidgetPredicate(
                (widget) => widget is ButtonStyleButton || widget is IconButton,
              )
              .evaluate()) {
        final render = element.findRenderObject();
        if (render is RenderBox && render.hasSize) {
          controls.add({
            'widget': element.widget.runtimeType.toString(),
            'width': render.size.width,
            'height': render.size.height,
            'below_44_logical_px':
                render.size.width < 44 || render.size.height < 44,
          });
        }
      }
      await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 1);
        final bytes = (await image.toByteData(
          format: ui.ImageByteFormat.png,
        ))!.buffer.asUint8List();
        await File('$outputPath/$name.png').writeAsBytes(bytes);
        image.dispose();
        manifest.add({
          'file': '$name.png',
          'state': state,
          'sha256': sha256.convert(bytes).toString(),
          'bytes': bytes.length,
          'width': 390,
          'height': 844,
          'text_scale': tester.platformDispatcher.textScaleFactor,
          'rendered_controls': controls,
        });
      });
    }

    ZenitAppController controllerFor(
      FakeGateway gateway,
      MemoryVault vault, {
      bool authenticated = true,
    }) => ZenitAppController(
      gateway: gateway,
      sessionStore: MemorySessionStore()
        ..value = authenticated ? validSession() : null,
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'gov-001-fixture',
      photoCapture: FakePhotoCapture(),
      clock: () => DateTime.utc(2026, 9, 13, 12),
    );

    final gateway = CaptureGateway();
    final vault = MemoryVault();
    final controller = controllerFor(gateway, vault, authenticated: false);
    await mount(controller);
    await capture('00-bootstrap-loading', 'bootstrap/loading');
    await controller.initialize();
    await tester.pumpAndSettle();
    await capture('01-login-idle', 'login/idle');
    gateway.loginFailure = const ZenitApiException(
      'Não foi possível entrar. Confira os dados e tente novamente.',
      statusCode: 401,
    );
    await controller.login('fixture@example.test', 'synthetic-placeholder');
    await tester.pumpAndSettle();
    await capture('02-login-error', 'login/fixture-401-error');
    gateway.loginFailure = null;
    await controller.login('fixture@example.test', 'synthetic-placeholder');
    await tester.pumpAndSettle();
    await capture('03-orders-empty', 'orders/empty');

    final order = preparedOrder();
    final plan = preparedMowingPlan();
    gateway.orders = [order];
    gateway.mowingPlans = [plan];
    await controller.refreshOrders();
    await tester.pumpAndSettle();
    await capture('04-orders-success', 'orders/success');
    await tester.tap(find.textContaining('somente rascunho'));
    await tester.pumpAndSettle();
    await capture('05-inspection-detail', 'inspection/local-detail');
    await tester.tap(find.text('1. Confirmar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2. Iniciar (GPS simulado)'));
    await tester.pumpAndSettle();
    for (var index = 0; index < 3; index++) {
      final field = find.byWidgetPredicate(
        (widget) =>
            widget is TextField &&
            widget.decoration?.labelText == 'Ponto ${index + 1} · altura (cm)',
      );
      await show(field);
      await tester.enterText(field, '${12 + index}');
    }
    await show(find.text('Salvar 3 rascunhos no aparelho'));
    await tester.tap(find.text('Salvar 3 rascunhos no aparelho'));
    await tester.pumpAndSettle();
    await capture(
      '06-inspection-measurements',
      'inspection/local-measurements',
    );
    for (var index = 0; index < 3; index++) {
      final button = find.text('Capturar foto preparada do ponto ${index + 1}');
      await show(button);
      await tester.tap(button);
      await tester.pumpAndSettle();
    }
    await capture('07-inspection-photos', 'inspection/fixture-photo-drafts');
    await show(find.text('3. Finalizar'), scrollDelta: -260);
    await tester.tap(find.text('3. Finalizar'));
    await tester.pumpAndSettle();
    await show(find.text('Sincronizar lote preparado'));
    await capture('08-inspection-ready-to-sync', 'inspection/local-only');
    gateway.syncFailure = const ZenitApiException(
      'Conexão indisponível. O lote preparado permanece no aparelho.',
    );
    await tester.tap(find.text('Sincronizar lote preparado'));
    await tester.pumpAndSettle();
    final pendingBatchId = vault.pendingBatch!.batchId;
    await capture('09-sync-pending', 'sync/transport-error-pending');
    await show(
      find.text(
        'Conexão indisponível. O lote preparado permanece no aparelho.',
      ),
    );
    await capture('10-sync-error', 'sync/actionable-fixture-error');
    gateway.syncFailure = null;
    await show(find.text('Sincronizar lote preparado'));
    await tester.tap(find.text('Sincronizar lote preparado'));
    await tester.pumpAndSettle();
    expect(gateway.lastBatch!.batchId, pendingBatchId);
    expect(vault.pendingBatch, isNull);
    await capture('11-sync-recovered', 'sync/same-batch-accepted');
    await show(find.text('Enviar fotos preparadas'));
    await tester.tap(find.text('Enviar fotos preparadas'));
    await tester.pumpAndSettle();
    await show(find.textContaining('Foto 1: conteúdo recebido, não validado'));
    await capture(
      '12-inspection-uploaded-unverified',
      'inspection/fixture-upload-receipts',
    );

    await mount(controller);
    await tester.pumpAndSettle();
    await show(find.textContaining('NÃO EXECUTÁVEL'));
    await tester.tap(find.textContaining('NÃO EXECUTÁVEL'));
    await tester.pumpAndSettle();
    await capture('13-mowing-plan', 'mowing/prepared-plan');
    await show(find.text('1. Confirmar ensaio'));
    await tester.tap(find.text('1. Confirmar ensaio'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('2. Iniciar (ponto simulado)'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Pausar ensaio'));
    await tester.pumpAndSettle();
    await capture('14-mowing-paused', 'mowing/simulated-pause');
    await tester.tap(find.text('Retomar ensaio'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('3. Finalizar ensaio'));
    await tester.pumpAndSettle();
    await show(find.text('Medições pós-serviço simuladas'));
    await capture(
      '15-post-service-empty',
      'post-service/simulated-height-fields',
    );
    for (var index = 0; index < 3; index++) {
      final field = find.byWidgetPredicate(
        (widget) =>
            widget is TextField &&
            widget.decoration?.labelText ==
                'Ponto ${index + 1} · altura pós-serviço (cm)',
      );
      await show(field);
      await tester.enterText(field, '${5 + index}');
    }
    await show(find.text('Salvar 3 medições simuladas'));
    await tester.tap(find.text('Salvar 3 medições simuladas'));
    await tester.pumpAndSettle();
    await show(find.text('Fotos pós-serviço simuladas'));
    await capture(
      '16-post-service-photos',
      'post-service/fixture-capture-controls',
    );

    await mount(controller);
    await tester.pumpAndSettle();
    gateway.logoutFailure = const ZenitApiException('Fixture network failure');
    await controller.logout();
    await tester.pumpAndSettle();
    expect(await vault.hasUnacknowledgedEvents(), isTrue);
    await capture('17-logout-offline', 'logout/remote-revocation-unconfirmed');
    await controller.login('fixture@example.test', 'synthetic-placeholder');
    await tester.pumpAndSettle();
    await capture('18-logout-recovered', 'session/same-user-retained-drafts');

    final conflictGateway = FakeGateway(orders: [order]);
    final conflictVault = MemoryVault();
    final conflictController = controllerFor(conflictGateway, conflictVault);
    await conflictController.initialize();
    await conflictController.confirmDemoOrder(order);
    await conflictController.startDemoOrder(order);
    await conflictController.saveThreeDrafts(order, [12, 13, 14]);
    for (final point in order.points) {
      await conflictController.capturePreparedPhoto(order, point);
    }
    await conflictController.finishDemoOrder(order);
    conflictGateway.syncResultFactory = (batch) => MobileSyncResult(
      batchId: batch.batchId,
      acceptedEventIds: batch.eventIds.skip(2).toSet(),
      rejectedEvents: {
        batch.eventIds.first: const SyncEventResult(
          code: 'fixture_rejected',
          message: 'Rejeição de teste: evidência preservada.',
        ),
      },
      conflictingEvents: {
        batch.eventIds[1]: const SyncEventResult(
          code: 'fixture_conflict',
          message: 'Conflito de teste: revisão necessária.',
        ),
      },
      nextSyncCursor: batch.baseSyncCursor + 1,
    );
    await conflictController.syncPreparedDrafts(order);
    await mount(conflictController);
    await tester.pumpAndSettle();
    await tester.tap(find.textContaining('somente rascunho'));
    await tester.pumpAndSettle();
    await show(find.textContaining('Confirmação: rejeitado pelo servidor'));
    await capture(
      '19-sync-rejected-conflict',
      'sync/persisted-rejection-and-conflict',
    );

    tester.platformDispatcher.textScaleFactorTestValue = 2;
    await mount(conflictController);
    await tester.pumpAndSettle();
    await capture('20-orders-text-scale-200', 'orders/text-scale-200');

    await tester.runAsync(() async {
      final sources = <Map<String, Object?>>[];
      for (final path in [
        'lib/main.dart',
        'lib/app_controller.dart',
        'test/support/fakes.dart',
        'tool/gov_001_capture_test.dart',
        fontPath,
      ]) {
        final bytes = await File(path).readAsBytes();
        sources.add({'path': path, 'sha256': sha256.convert(bytes).toString()});
      }
      await File('$outputPath/manifest.json').writeAsString(
        const JsonEncoder.withIndent('  ').convert({
          'ticket': 'GOV-001',
          'captured_at_utc': DateTime.now().toUtc().toIso8601String(),
          'evidence_type': 'fixture-rendered Flutter widget snapshots',
          'data_status': 'simulated',
          'eligible_for_field_execution': false,
          'eligible_for_model_training': false,
          'eligible_for_official_reporting': false,
          'limitations': [
            'Memory vault and fake gateway; no real network, encryption or device assertion.',
            'Photo fake is a four-byte signature; no camera image or preview validation.',
            'Roboto loaded only in the capture harness; no app theme changes.',
            'No device, TalkBack, sunlight, platform keyboard or process-kill verification.',
          ],
          'sources': sources,
          'captures': manifest,
        }),
      );
    });
  });
}
