import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/app_controller.dart';
import 'package:zenit_mobile/data/zenit_gateway.dart';
import 'package:zenit_mobile/domain/auth_session.dart';
import 'package:zenit_mobile/domain/measurement_draft.dart';
import 'package:zenit_mobile/domain/mobile_sync.dart';
import 'package:zenit_mobile/domain/prepared_work_order.dart';

import 'support/fakes.dart';

void main() {
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
        uuidFactory: _uuidFactory(),
        clock: () => DateTime.utc(2026, 8, 9, 14),
      );
      await controller.initialize();

      expect(await controller.login('field@example.test', 'secret'), isTrue);
      expect(vault.orders.single.id, order.id);
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
      uuidFactory: _uuidFactory(),
    );
    await controller.initialize();

    expect(await controller.login('field@example.test', 'secret'), isTrue);
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
      uuidFactory: _uuidFactory(),
    );
    await controller.initialize();
    await controller.login('field@example.test', 'secret');
    await controller.saveThreeDrafts(order, [8, 22, 35]);

    expect(await controller.syncPreparedDrafts(order), isFalse);
    final firstBatch = vault.pendingBatch!;
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
    expect(vault.pendingBatch, isNull);
    expect(vault.syncCursor, 1);
    expect(
      (await vault.readDrafts(
        order.id,
      )).every((draft) => draft.syncState == DraftSyncState.acknowledged),
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
      uuidFactory: _uuidFactory(),
    );
    await controller.initialize();
    await controller.login('field@example.test', 'secret');
    await controller.saveThreeDrafts(order, [8, 22, 35]);
    await controller.syncPreparedDrafts(order);

    expect(await controller.saveThreeDrafts(order, [9, 23, 36]), isFalse);
    expect(controller.errorMessage, contains('não pode ser sobrescrita'));
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
          acceptedEventIds: {batch.eventIds[0]},
          rejectedEvents: {
            batch.eventIds[1]: const SyncEventResult(
              code: 'road_access_denied',
              message: 'access denied',
            ),
          },
          conflictingEvents: {
            batch.eventIds[2]: const SyncEventResult(
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
        uuidFactory: _uuidFactory(),
      );
      await controller.initialize();
      await controller.login('field@example.test', 'secret');
      await controller.saveThreeDrafts(order, [8, 22, 35]);

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
    );

    await controller.initialize();

    expect(controller.isAuthenticated, isFalse);
    expect(sessionStore.value, isNull);
    expect(controller.errorMessage, contains('não corresponde'));
    expect(vault.orders, isNotEmpty);
  });
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
  Future<void> registerDevice(
    String accessToken,
    String deviceId,
    String appVersion,
  ) => throw UnimplementedError();

  @override
  Future<MobileSyncResult> syncBatch(
    String accessToken,
    PendingSyncBatch batch,
    List<MeasurementDraft> drafts,
  ) => throw UnimplementedError();
}
