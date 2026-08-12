import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/app_controller.dart';
import 'package:zenit_mobile/data/zenit_gateway.dart';
import 'package:zenit_mobile/domain/auth_session.dart';
import 'package:zenit_mobile/domain/measurement_draft.dart';
import 'package:zenit_mobile/domain/mobile_sync.dart';
import 'package:zenit_mobile/domain/mowing_demo_lifecycle.dart';
import 'package:zenit_mobile/domain/prepared_mowing_plan.dart';
import 'package:zenit_mobile/domain/prepared_photo_draft.dart';
import 'package:zenit_mobile/domain/prepared_work_order.dart';

import 'support/fakes.dart';

void main() {
  test(
    'mowing rehearsal persists balanced offline events and retries IDs',
    () async {
      final order = preparedOrder();
      final plan = preparedMowingPlan();
      final vault = MemoryVault();
      final gateway = FakeGateway(
        orders: [order],
        mowingPlans: [plan],
        syncFailure: const ZenitApiException('offline'),
      );
      final controller = ZenitAppController(
        gateway: gateway,
        sessionStore: MemorySessionStore(),
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        uuidFactory: _uuidFactory(),
        clock: () => DateTime.utc(2026, 8, 11, 14),
      );
      await controller.initialize();
      await controller.login('field@example.test', 'secret');

      expect(await controller.confirmMowingDemo(plan), isTrue);
      expect(await controller.startMowingDemo(plan), isTrue);
      expect(await controller.pauseMowingDemo(plan), isTrue);
      expect(await controller.resumeMowingDemo(plan), isTrue);
      expect(await controller.finishMowingDemo(plan), isTrue);
      expect(
        await controller.saveThreeMowingPostServiceMeasurements(plan, [
          7,
          8,
          9,
        ]),
        isTrue,
      );
      expect(await controller.syncMowingDemo(plan), isFalse);

      final firstBatch = vault.pendingBatch!;
      final pendingEvents = await vault.readMowingLifecycleEvents(plan.id);
      final pendingMeasurements = await vault.readMowingPostServiceMeasurements(
        plan.id,
      );
      expect(firstBatch.eventIds, hasLength(8));
      expect(pendingEvents.map((event) => event.operation), [
        MowingDemoOperation.confirm,
        MowingDemoOperation.start,
        MowingDemoOperation.pause,
        MowingDemoOperation.resume,
        MowingDemoOperation.finish,
      ]);
      expect(pendingEvents[1].simulatedLatitude, order.points.first.latitude);
      expect(pendingEvents[1].simulatedLongitude, order.points.first.longitude);
      expect(
        pendingEvents.every(
          (event) => event.syncState == DraftSyncState.pending,
        ),
        isTrue,
      );
      expect(pendingMeasurements, hasLength(3));
      expect(pendingMeasurements.map((item) => item.heightCm), [7, 8, 9]);
      expect(
        pendingMeasurements.every(
          (item) => item.syncState == DraftSyncState.pending,
        ),
        isTrue,
      );
      expect(await vault.hasUnacknowledgedEvents(), isTrue);

      gateway.syncFailure = null;
      expect(await controller.syncMowingDemo(plan), isTrue);
      expect(gateway.lastBatch!.batchId, firstBatch.batchId);
      expect(gateway.lastBatch!.eventIds, firstBatch.eventIds);
      expect(gateway.lastEvents!.map((event) => event['operation']), [
        'confirm',
        'start',
        'pause',
        'resume',
        'finish',
        'create',
        'create',
        'create',
      ]);
      final lifecyclePayloads = gateway.lastEvents!
          .take(5)
          .map((event) => (event['payload']! as Map).cast<String, Object?>());
      expect(
        lifecyclePayloads.every(
          (payload) =>
              payload['data_status'] == 'simulated' &&
              payload['rehearsal_scope'] == 'mowing_demo_rehearsal_only' &&
              payload['operational_approval_satisfied'] == false &&
              payload['authorizes_field_work'] == false &&
              payload['eligible_for_field_execution'] == false &&
              payload['eligible_for_model_training'] == false &&
              payload['eligible_for_official_reporting'] == false,
        ),
        isTrue,
      );
      expect(
        gateway.lastEvents!.skip(5).map((event) => event['entity_type']),
        everyElement('mowing_measurement'),
      );
      final measurementPayloads = gateway.lastEvents!
          .skip(5)
          .map((event) => (event['payload']! as Map).cast<String, Object?>());
      expect(
        measurementPayloads.every(
          (payload) =>
              payload['phase'] == 'post_service' &&
              payload['measurement_scope'] == 'mowing_demo_post_service_only' &&
              payload['location_status'] == 'not_collected' &&
              payload['photo_status'] == 'not_collected' &&
              payload['data_status'] == 'simulated' &&
              payload['quality_status'] == 'simulated_unverified' &&
              payload['operational_approval_satisfied'] == false &&
              payload['authorizes_field_work'] == false &&
              payload['eligible_for_field_execution'] == false &&
              payload['eligible_for_model_training'] == false &&
              payload['eligible_for_official_reporting'] == false,
        ),
        isTrue,
      );
      expect(vault.pendingBatch, isNull);
      expect(vault.syncCursor, 1);
      expect(
        (await vault.readMowingLifecycleEvents(
          plan.id,
        )).every((event) => event.syncState == DraftSyncState.acknowledged),
        isTrue,
      );
      expect(
        (await vault.readMowingPostServiceMeasurements(
          plan.id,
        )).every((item) => item.syncState == DraftSyncState.acknowledged),
        isTrue,
      );
    },
  );

  test(
    'acknowledged mowing lifecycle syncs only new post-service measurements',
    () async {
      final order = preparedOrder();
      final plan = preparedMowingPlan();
      final vault = MemoryVault();
      final gateway = FakeGateway(orders: [order], mowingPlans: [plan]);
      final controller = ZenitAppController(
        gateway: gateway,
        sessionStore: MemorySessionStore(),
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        uuidFactory: _uuidFactory(),
        clock: () => DateTime.utc(2026, 8, 11, 14),
      );
      await controller.initialize();
      await controller.login('field@example.test', 'secret');

      expect(await controller.confirmMowingDemo(plan), isTrue);
      expect(await controller.startMowingDemo(plan), isTrue);
      expect(await controller.finishMowingDemo(plan), isTrue);
      final lifecycle = await vault.readMowingLifecycleEvents(plan.id);
      await vault.replaceMowingLifecycleEvents(
        plan.id,
        lifecycle
            .map(
              (event) => event.copyWith(
                syncState: DraftSyncState.acknowledged,
                syncResultCode: 'persisted',
              ),
            )
            .toList(),
      );

      expect(
        await controller.saveThreeMowingPostServiceMeasurements(plan, [
          5,
          6,
          7,
        ]),
        isTrue,
      );
      expect(await controller.syncMowingDemo(plan), isTrue);

      expect(gateway.lastBatch!.eventIds, hasLength(3));
      expect(
        gateway.lastEvents!.map((event) => event['entity_type']),
        everyElement('mowing_measurement'),
      );
      expect(
        (await vault.readMowingLifecycleEvents(
          plan.id,
        )).every((event) => event.syncState == DraftSyncState.acknowledged),
        isTrue,
      );
    },
  );

  test('refresh retains mowing point provenance required by a retry', () async {
    final order = preparedOrder();
    final plan = preparedMowingPlan();
    final vault = MemoryVault()
      ..orders = [order]
      ..mowingPlans = [plan]
      ..mowingLifecycleEvents[plan.id] = [
        MowingDemoLifecycleEvent(
          eventId: '10000000-0000-4000-8000-000000000001',
          mowingOrderId: plan.id,
          sourcePlanningApprovalId: plan.planningApprovalId!,
          operation: MowingDemoOperation.confirm,
          occurredAt: DateTime.utc(2026, 8, 12, 14),
        ),
      ];
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: const [], mowingPlans: [plan]),
      sessionStore: MemorySessionStore()..value = validSession(),
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
    );

    await controller.initialize();

    expect(vault.orders.single.id, plan.sourceInspectionWorkOrderId);
    expect(controller.orders.single.id, plan.sourceInspectionWorkOrderId);
  });

  test(
    'mowing post-service measurements require a finished rehearsal',
    () async {
      final order = preparedOrder();
      final plan = preparedMowingPlan();
      final controller = ZenitAppController(
        gateway: FakeGateway(orders: [order], mowingPlans: [plan]),
        sessionStore: MemorySessionStore(),
        vault: MemoryVault(),
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        uuidFactory: _uuidFactory(),
        clock: () => DateTime.utc(2026, 8, 11, 14),
      );
      await controller.initialize();
      await controller.login('field@example.test', 'secret');
      await controller.confirmMowingDemo(plan);
      await controller.startMowingDemo(plan);

      expect(
        await controller.saveThreeMowingPostServiceMeasurements(plan, [
          5,
          6,
          7,
        ]),
        isFalse,
      );
      expect(controller.errorMessage, contains('Finalize um ensaio'));
    },
  );

  test(
    'mowing rehearsal fails closed without effective safe planning',
    () async {
      final blockedPlan = PreparedMowingPlan.fromJson(
        preparedMowingPlanJson()..['latest_safety_result'] = 'inconclusive',
      );
      final controller = ZenitAppController(
        gateway: FakeGateway(
          orders: [preparedOrder()],
          mowingPlans: [blockedPlan],
        ),
        sessionStore: MemorySessionStore(),
        vault: MemoryVault(),
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
      );
      await controller.initialize();
      await controller.login('field@example.test', 'secret');

      expect(await controller.confirmMowingDemo(blockedPlan), isFalse);
      expect(controller.errorMessage, contains('clima e segurança'));
    },
  );

  test('downloads and retains a read-only mowing planning snapshot', () async {
    final plan = preparedMowingPlan();
    final vault = MemoryVault();
    final controller = ZenitAppController(
      gateway: FakeGateway(mowingPlans: [plan]),
      sessionStore: MemorySessionStore(),
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
    );
    await controller.initialize();

    expect(await controller.login('field@example.test', 'secret'), isTrue);
    expect(controller.mowingPlans.single.id, plan.id);
    expect((await vault.readMowingPlans()).single.id, plan.id);

    await controller.logout();
    expect(controller.mowingPlans, isEmpty);
    expect((await vault.readMowingPlans()).single.id, plan.id);
  });

  test(
    'downloads an order and stores three local-only prepared drafts',
    () async {
      final order = preparedOrder();
      final vault = MemoryVault();
      final controller = ZenitAppController(
        gateway: FakeGateway(orders: [order]),
        sessionStore: MemorySessionStore(),
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        photoCapture: FakePhotoCapture(),
        uuidFactory: _uuidFactory(),
        clock: () => DateTime.utc(2026, 8, 9, 14),
      );
      await controller.initialize();

      expect(await controller.login('field@example.test', 'secret'), isTrue);
      expect(vault.orders.single.id, order.id);
      await _startDemo(controller, order);
      expect(await controller.saveThreeDrafts(order, [8, 22, 35]), isTrue);

      final drafts = await vault.readDrafts(order.id);
      expect(drafts, hasLength(3));
      expect(drafts.map((draft) => draft.dataStatus).toSet(), {'prepared'});
      expect(drafts.map((draft) => draft.syncState).toSet(), {
        DraftSyncState.localOnly,
      });
      expect(
        drafts.every((draft) => !draft.eligibleForOfficialReporting),
        isTrue,
      );
    },
  );

  test('logout removes the session but retains encrypted local data', () async {
    final vault = MemoryVault()..orders = [preparedOrder()];
    final sessionStore = MemorySessionStore()..value = validSession();
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [preparedOrder()]),
      sessionStore: sessionStore,
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
    );
    await controller.initialize();
    await controller.logout();

    expect(sessionStore.value, isNull);
    expect(vault.orders, isNotEmpty);
    expect(controller.orders, isEmpty);
    expect(controller.isAuthenticated, isFalse);
  });

  test(
    'an unauthorized refresh removes session access but retains encrypted cache',
    () async {
      final vault = MemoryVault()..orders = [preparedOrder()];
      final sessionStore = MemorySessionStore()..value = validSession();
      final controller = ZenitAppController(
        gateway: _UnauthorizedGateway(),
        sessionStore: sessionStore,
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        photoCapture: FakePhotoCapture(),
      );
      await controller.initialize();

      expect(controller.isAuthenticated, isFalse);
      expect(sessionStore.value, isNull);
      expect(vault.orders, isNotEmpty);
      expect(controller.orders, isEmpty);
    },
  );

  test(
    'missing session hides but retains the encrypted order snapshot',
    () async {
      final vault = MemoryVault()..orders = [preparedOrder()];
      final controller = ZenitAppController(
        gateway: FakeGateway(),
        sessionStore: MemorySessionStore(),
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        photoCapture: FakePhotoCapture(),
      );
      await controller.initialize();

      expect(controller.orders, isEmpty);
      expect(vault.orders, isNotEmpty);
    },
  );

  test('zero centimeters remains a valid N1 prepared measurement', () async {
    final order = preparedOrder();
    final vault = MemoryVault();
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [order]),
      sessionStore: MemorySessionStore(),
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
      uuidFactory: _uuidFactory(),
    );
    await controller.initialize();

    expect(await controller.login('field@example.test', 'secret'), isTrue);
    await _startDemo(controller, order);
    expect(await controller.saveThreeDrafts(order, [0, 9.9, 30]), isTrue);
    expect((await vault.readDrafts(order.id)).first.heightCm, 0);
  });

  test('network retry reuses persisted batch and event identifiers', () async {
    final order = preparedOrder();
    final vault = MemoryVault();
    final gateway = FakeGateway(
      orders: [order],
      syncFailure: const ZenitApiException('offline'),
    );
    final controller = ZenitAppController(
      gateway: gateway,
      sessionStore: MemorySessionStore(),
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
      uuidFactory: _uuidFactory(),
    );
    await controller.initialize();
    await controller.login('field@example.test', 'secret');
    await _startDemo(controller, order);
    await controller.saveThreeDrafts(order, [8, 22, 35]);
    await _capturePhotos(controller, order);
    await controller.finishDemoOrder(order);

    expect(await controller.syncPreparedDrafts(order), isFalse);
    final firstBatch = vault.pendingBatch!;
    expect(firstBatch.eventIds, hasLength(9));
    expect(
      (await vault.readDrafts(
        order.id,
      )).every((draft) => draft.syncState == DraftSyncState.pending),
      isTrue,
    );

    gateway.syncFailure = null;
    expect(await controller.syncPreparedDrafts(order), isTrue);

    expect(gateway.lastBatch!.batchId, firstBatch.batchId);
    expect(gateway.lastBatch!.eventIds, firstBatch.eventIds);
    expect(gateway.lastEvents!.map((event) => event['operation']).toList(), [
      'confirm',
      'start',
      'create',
      'prepare',
      'create',
      'prepare',
      'create',
      'prepare',
      'finish',
    ]);
    final photoPayloads = gateway.lastEvents!
        .where((event) => event['operation'] == 'prepare')
        .map((event) => (event['payload']! as Map).cast<String, Object?>());
    expect(photoPayloads, hasLength(3));
    expect(
      photoPayloads.every(
        (payload) =>
            payload['content_status'] == 'not_uploaded' &&
            payload['ruler_status'] == 'not_validated' &&
            !payload.containsKey('content_base64'),
      ),
      isTrue,
    );
    expect(vault.pendingBatch, isNull);
    expect(vault.syncCursor, 1);
    expect(
      (await vault.readDrafts(
        order.id,
      )).every((draft) => draft.syncState == DraftSyncState.acknowledged),
      isTrue,
    );
    expect(
      (await vault.readLifecycleEvents(
        order.id,
      )).every((event) => event.syncState == DraftSyncState.acknowledged),
      isTrue,
    );
    expect(
      (await vault.readPhotoDrafts(
        order.id,
      )).every((photo) => photo.syncState == DraftSyncState.acknowledged),
      isTrue,
    );
  });

  test('persistent acknowledgement prevents overwriting an event', () async {
    final order = preparedOrder();
    final vault = MemoryVault();
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [order]),
      sessionStore: MemorySessionStore(),
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
      uuidFactory: _uuidFactory(),
    );
    await controller.initialize();
    await controller.login('field@example.test', 'secret');
    await _startDemo(controller, order);
    await controller.saveThreeDrafts(order, [8, 22, 35]);
    await _capturePhotos(controller, order);
    await controller.finishDemoOrder(order);
    await controller.syncPreparedDrafts(order);

    expect(await controller.saveThreeDrafts(order, [9, 23, 36]), isFalse);
    expect(controller.errorMessage, contains('não pode ser sobrescrita'));
  });

  test(
    'uploads only acknowledged manifests and resumes after failure',
    () async {
      final order = preparedOrder();
      final vault = MemoryVault();
      final gateway = FakeGateway(orders: [order]);
      final controller = ZenitAppController(
        gateway: gateway,
        sessionStore: MemorySessionStore(),
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        photoCapture: FakePhotoCapture(),
        uuidFactory: _uuidFactory(),
      );
      await controller.initialize();
      await controller.login('field@example.test', 'secret');
      await _startDemo(controller, order);
      await controller.saveThreeDrafts(order, [8, 22, 35]);
      await _capturePhotos(controller, order);
      await controller.finishDemoOrder(order);

      expect(await controller.uploadPreparedPhotos(order), isFalse);
      expect(gateway.uploadCalls, 0);
      expect(await controller.syncPreparedDrafts(order), isTrue);

      gateway.uploadFailure = const ZenitApiException('offline');
      gateway.uploadFailureAtCall = 2;
      expect(await controller.uploadPreparedPhotos(order), isFalse);
      expect(gateway.uploadCalls, 2);
      expect(
        (await vault.readPhotoDrafts(
          order.id,
        )).where((photo) => photo.isUploaded).map((photo) => photo.sequence),
        [1],
      );

      gateway.uploadFailure = null;
      expect(await controller.uploadPreparedPhotos(order), isTrue);
      expect(gateway.uploadCalls, 4);
      final uploaded = await vault.readPhotoDrafts(order.id);
      expect(uploaded.every((photo) => photo.isUploaded), isTrue);
      expect(
        uploaded.every(
          (photo) => photo.toJson()['eligible_for_official_reporting'] == false,
        ),
        isTrue,
      );

      expect(await controller.uploadPreparedPhotos(order), isTrue);
      expect(gateway.uploadCalls, 4);
    },
  );

  test('demo cannot finish without one photo per planned point', () async {
    final order = preparedOrder();
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [order]),
      sessionStore: MemorySessionStore(),
      vault: MemoryVault(),
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
      uuidFactory: _uuidFactory(),
    );
    await controller.initialize();
    await controller.login('field@example.test', 'secret');
    await _startDemo(controller, order);
    await controller.saveThreeDrafts(order, [8, 22, 35]);

    expect(await controller.finishDemoOrder(order), isFalse);
    expect(controller.errorMessage, contains('foto preparada'));
  });

  test(
    'rejected and conflicting persistent outcomes are retained locally',
    () async {
      final order = preparedOrder();
      final vault = MemoryVault();
      final gateway = FakeGateway(
        orders: [order],
        syncResultFactory: (batch) => MobileSyncResult(
          batchId: batch.batchId,
          acceptedEventIds: {
            batch.eventIds[0],
            batch.eventIds[1],
            batch.eventIds[2],
            batch.eventIds[3],
            batch.eventIds[5],
            batch.eventIds[7],
            batch.eventIds[8],
          },
          rejectedEvents: {
            batch.eventIds[4]: const SyncEventResult(
              code: 'road_access_denied',
              message: 'access denied',
            ),
          },
          conflictingEvents: {
            batch.eventIds[6]: const SyncEventResult(
              code: 'event_id_reused',
              message: 'conflict preserved',
            ),
          },
          nextSyncCursor: 1,
        ),
      );
      final controller = ZenitAppController(
        gateway: gateway,
        sessionStore: MemorySessionStore(),
        vault: vault,
        deviceIdentityStore: MemoryDeviceIdentityStore(),
        appVersion: 'test',
        photoCapture: FakePhotoCapture(),
        uuidFactory: _uuidFactory(),
      );
      await controller.initialize();
      await controller.login('field@example.test', 'secret');
      await _startDemo(controller, order);
      await controller.saveThreeDrafts(order, [8, 22, 35]);
      await _capturePhotos(controller, order);
      await controller.finishDemoOrder(order);

      expect(await controller.syncPreparedDrafts(order), isTrue);

      final states = (await vault.readDrafts(
        order.id,
      )).map((draft) => draft.syncState).toList();
      expect(states, [
        DraftSyncState.acknowledged,
        DraftSyncState.rejected,
        DraftSyncState.conflict,
      ]);
      expect(vault.pendingBatch, isNull);
    },
  );

  test('different user cannot erase an unacknowledged local event', () async {
    final order = preparedOrder();
    final vault = MemoryVault()
      ..ownerUserId = '77777777-7777-4777-8777-777777777777'
      ..orders = [order]
      ..drafts[order.id] = [
        MeasurementDraft(
          eventId: '66666666-6666-4666-8666-666666666666',
          orderId: order.id,
          plannedPointId: order.points.first.id,
          sequence: 1,
          heightCm: 10,
          recordedAt: DateTime.utc(2026, 8, 9),
        ),
      ];
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [order]),
      sessionStore: MemorySessionStore(),
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
    );
    await controller.initialize();

    expect(await controller.login('field@example.test', 'secret'), isFalse);
    expect(controller.errorMessage, contains('outro usuário'));
    expect(vault.drafts[order.id], isNotEmpty);
    expect(vault.ownerUserId, '77777777-7777-4777-8777-777777777777');
  });

  test('restored session cannot open another user encrypted vault', () async {
    final vault = MemoryVault()
      ..ownerUserId = '77777777-7777-4777-8777-777777777777'
      ..orders = [preparedOrder()];
    final sessionStore = MemorySessionStore()..value = validSession();
    final controller = ZenitAppController(
      gateway: FakeGateway(orders: [preparedOrder()]),
      sessionStore: sessionStore,
      vault: vault,
      deviceIdentityStore: MemoryDeviceIdentityStore(),
      appVersion: 'test',
      photoCapture: FakePhotoCapture(),
    );

    await controller.initialize();

    expect(controller.isAuthenticated, isFalse);
    expect(sessionStore.value, isNull);
    expect(controller.errorMessage, contains('não corresponde'));
    expect(vault.orders, isNotEmpty);
  });
}

Future<void> _startDemo(
  ZenitAppController controller,
  PreparedWorkOrder order,
) async {
  expect(await controller.confirmDemoOrder(order), isTrue);
  expect(await controller.startDemoOrder(order), isTrue);
}

Future<void> _capturePhotos(
  ZenitAppController controller,
  PreparedWorkOrder order,
) async {
  for (final point in order.points) {
    expect(await controller.capturePreparedPhoto(order, point), isTrue);
  }
}

String Function() _uuidFactory() {
  var counter = 0;
  return () {
    counter++;
    return '55555555-5555-4555-8555-${counter.toString().padLeft(12, '0')}';
  };
}

class _UnauthorizedGateway implements ZenitGateway {
  @override
  Future<AuthSession> login(String email, String password) =>
      throw UnimplementedError();

  @override
  Future<List<PreparedWorkOrder>> listPreparedOrders(String accessToken) =>
      throw const ZenitApiException('Expired token', statusCode: 401);

  @override
  Future<List<PreparedMowingPlan>> listPreparedMowingPlans(
    String accessToken,
  ) => throw const ZenitApiException('Expired token', statusCode: 401);

  @override
  Future<void> registerDevice(
    String accessToken,
    String deviceId,
    String appVersion,
  ) => throw UnimplementedError();

  @override
  Future<MobileSyncResult> syncBatch(
    String accessToken,
    PendingSyncBatch batch,
    List<Map<String, Object?>> events,
  ) => throw UnimplementedError();

  @override
  Future<void> uploadPreparedPhoto(
    String accessToken,
    String deviceId,
    PreparedPhotoDraft photo,
  ) => throw UnimplementedError();
}
