import 'package:flutter/foundation.dart';

import 'data/offline_vault.dart';
import 'data/photo_capture.dart';
import 'data/device_identity_store.dart';
import 'data/secure_session_store.dart';
import 'data/zenit_gateway.dart';
import 'domain/auth_session.dart';
import 'domain/demo_order_lifecycle.dart';
import 'domain/measurement_draft.dart';
import 'domain/mobile_sync.dart';
import 'domain/mowing_demo_lifecycle.dart';
import 'domain/mowing_post_service_measurement_draft.dart';
import 'domain/prepared_mowing_plan.dart';
import 'domain/prepared_photo_draft.dart';
import 'domain/prepared_work_order.dart';

class ZenitAppController extends ChangeNotifier {
  ZenitAppController({
    required this.gateway,
    required this.sessionStore,
    required this.vault,
    required this.deviceIdentityStore,
    required this.appVersion,
    PhotoCapture? photoCapture,
    DateTime Function()? clock,
    String Function()? uuidFactory,
  }) : _clock = clock ?? DateTime.now,
       _uuidFactory = uuidFactory ?? generateUuidV4,
       _photoCapture = photoCapture ?? ImagePickerPhotoCapture();

  final ZenitGateway gateway;
  final SessionStore sessionStore;
  final OfflineVault vault;
  final DeviceIdentityStore deviceIdentityStore;
  final String appVersion;
  final DateTime Function() _clock;
  final String Function() _uuidFactory;
  final PhotoCapture _photoCapture;

  AuthSession? session;
  List<PreparedWorkOrder> orders = const [];
  List<PreparedMowingPlan> mowingPlans = const [];
  bool initializing = true;
  bool busy = false;
  String? errorMessage;

  bool get isAuthenticated => session != null;

  Future<void> initialize() async {
    try {
      await vault.initialize();
      orders = await vault.readOrders();
      mowingPlans = await vault.readMowingPlans();
      session = await sessionStore.readValid(_clock());
      if (session != null) {
        final ownerUserId = await vault.readOwnerUserId();
        if (ownerUserId != null && ownerUserId != session!.userId) {
          await _invalidateSession();
          errorMessage =
              'A sessão não corresponde ao proprietário dos dados criptografados.';
        } else {
          if (ownerUserId == null) {
            await vault.bindOwnerUserId(session!.userId);
          }
          await refreshOrders(silent: true);
        }
      } else {
        orders = const [];
        mowingPlans = const [];
      }
    } catch (error) {
      errorMessage = 'Falha ao abrir o armazenamento seguro: $error';
    } finally {
      initializing = false;
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    return _run(() async {
      final authenticated = await gateway.login(email, password);
      final downloaded = await _downloadPreparedSnapshots(
        authenticated.accessToken,
      );
      final ownerUserId = await vault.readOwnerUserId();
      if (ownerUserId != null && ownerUserId != authenticated.userId) {
        if (await vault.hasUnacknowledgedEvents()) {
          throw const LocalPendingEventsError();
        }
        await vault.clearUserData();
        await deviceIdentityStore.clear();
      }
      await vault.bindOwnerUserId(authenticated.userId);
      await vault.replaceOrders(downloaded.orders);
      await vault.replaceMowingPlans(downloaded.mowingPlans);
      await sessionStore.write(authenticated);
      session = authenticated;
      orders = await vault.readOrders();
      mowingPlans = await vault.readMowingPlans();
    });
  }

  Future<bool> refreshOrders({bool silent = false}) async {
    final current = session;
    if (current == null) return false;
    if (silent) {
      try {
        final downloaded = await _downloadPreparedSnapshots(
          current.accessToken,
        );
        await vault.replaceOrders(downloaded.orders);
        await vault.replaceMowingPlans(downloaded.mowingPlans);
        orders = await vault.readOrders();
        mowingPlans = await vault.readMowingPlans();
        notifyListeners();
        return true;
      } catch (error) {
        if (error is ZenitApiException && error.statusCode == 401) {
          await _invalidateSession();
        }
        return false;
      }
    }
    return _run(() async {
      final downloaded = await _downloadPreparedSnapshots(current.accessToken);
      await vault.replaceOrders(downloaded.orders);
      await vault.replaceMowingPlans(downloaded.mowingPlans);
      orders = await vault.readOrders();
      mowingPlans = await vault.readMowingPlans();
    });
  }

  Future<void> logout() async {
    await _invalidateSession();
    errorMessage = null;
    notifyListeners();
  }

  Future<void> _invalidateSession() async {
    await sessionStore.clear();
    session = null;
    orders = const [];
    mowingPlans = const [];
  }

  Future<
    ({List<PreparedWorkOrder> orders, List<PreparedMowingPlan> mowingPlans})
  >
  _downloadPreparedSnapshots(String accessToken) async {
    final downloadedOrders = await gateway.listPreparedOrders(accessToken);
    final downloadedMowingPlans = await gateway.listPreparedMowingPlans(
      accessToken,
    );
    return (orders: downloadedOrders, mowingPlans: downloadedMowingPlans);
  }

  Future<List<MeasurementDraft>> readDrafts(String orderId) =>
      vault.readDrafts(orderId);

  Future<List<DemoLifecycleEvent>> readLifecycleEvents(String orderId) =>
      vault.readLifecycleEvents(orderId);

  Future<List<PreparedPhotoDraft>> readPhotoDrafts(String orderId) =>
      vault.readPhotoDrafts(orderId);

  Future<List<MowingDemoLifecycleEvent>> readMowingLifecycleEvents(
    String mowingOrderId,
  ) => vault.readMowingLifecycleEvents(mowingOrderId);

  Future<List<MowingPostServiceMeasurementDraft>>
  readMowingPostServiceMeasurements(String mowingOrderId) =>
      vault.readMowingPostServiceMeasurements(mowingOrderId);

  Future<bool> confirmMowingDemo(PreparedMowingPlan plan) => _run(() async {
    await _prepareMowingDemoTransition(plan);
    final events = await vault.readMowingLifecycleEvents(plan.id);
    if (events.isNotEmpty) throw const InvalidMowingDemoLifecycleError();
    await vault.replaceMowingLifecycleEvents(plan.id, [
      _newMowingDemoEvent(plan, MowingDemoOperation.confirm),
    ]);
  });

  Future<bool> startMowingDemo(PreparedMowingPlan plan) => _run(() async {
    final sourceOrder = await _prepareMowingDemoTransition(plan);
    final events = await vault.readMowingLifecycleEvents(plan.id);
    if (events.length != 1 ||
        events.single.operation != MowingDemoOperation.confirm) {
      throw const InvalidMowingDemoLifecycleError();
    }
    final demoPoint = sourceOrder.points.first;
    await vault.replaceMowingLifecycleEvents(plan.id, [
      ...events,
      _newMowingDemoEvent(
        plan,
        MowingDemoOperation.start,
        notBefore: events.last.occurredAt,
        simulatedLatitude: demoPoint.latitude,
        simulatedLongitude: demoPoint.longitude,
      ),
    ]);
  });

  Future<bool> pauseMowingDemo(PreparedMowingPlan plan) =>
      _appendMowingDemoTransition(plan, MowingDemoOperation.pause, const {
        MowingDemoOperation.start,
        MowingDemoOperation.resume,
      });

  Future<bool> resumeMowingDemo(PreparedMowingPlan plan) =>
      _appendMowingDemoTransition(plan, MowingDemoOperation.resume, const {
        MowingDemoOperation.pause,
      });

  Future<bool> finishMowingDemo(PreparedMowingPlan plan) =>
      _appendMowingDemoTransition(plan, MowingDemoOperation.finish, const {
        MowingDemoOperation.start,
        MowingDemoOperation.resume,
      });

  Future<bool> _appendMowingDemoTransition(
    PreparedMowingPlan plan,
    MowingDemoOperation operation,
    Set<MowingDemoOperation> allowedPrevious,
  ) => _run(() async {
    await _prepareMowingDemoTransition(plan);
    final events = await vault.readMowingLifecycleEvents(plan.id);
    if (events.isEmpty || !allowedPrevious.contains(events.last.operation)) {
      throw const InvalidMowingDemoLifecycleError();
    }
    await vault.replaceMowingLifecycleEvents(plan.id, [
      ...events,
      _newMowingDemoEvent(plan, operation, notBefore: events.last.occurredAt),
    ]);
  });

  Future<PreparedWorkOrder> _prepareMowingDemoTransition(
    PreparedMowingPlan plan,
  ) async {
    if (!plan.canRunDemoRehearsal) {
      throw const MowingDemoNotEligibleError();
    }
    if (await vault.readPendingSyncBatch() != null) {
      throw const PendingBatchEditError();
    }
    final matchingOrders = orders.where(
      (order) => order.id == plan.sourceInspectionWorkOrderId,
    );
    if (matchingOrders.length != 1) {
      throw const MowingDemoSourcePointError();
    }
    final events = await vault.readMowingLifecycleEvents(plan.id);
    if (events.any((event) => event.syncState != DraftSyncState.localOnly)) {
      throw const PersistedMowingDemoEditError();
    }
    return matchingOrders.single;
  }

  MowingDemoLifecycleEvent _newMowingDemoEvent(
    PreparedMowingPlan plan,
    MowingDemoOperation operation, {
    DateTime? notBefore,
    double? simulatedLatitude,
    double? simulatedLongitude,
  }) {
    final planningApprovalId = plan.planningApprovalId;
    if (planningApprovalId == null) throw const MowingDemoNotEligibleError();
    final occurredAt = _clock().toUtc();
    if (notBefore != null && occurredAt.isBefore(notBefore)) {
      throw const InvalidMowingDemoTimeError();
    }
    return MowingDemoLifecycleEvent(
      eventId: _uuidFactory(),
      mowingOrderId: plan.id,
      sourcePlanningApprovalId: planningApprovalId,
      operation: operation,
      occurredAt: occurredAt,
      simulatedLatitude: simulatedLatitude,
      simulatedLongitude: simulatedLongitude,
    );
  }

  Future<bool> saveThreeMowingPostServiceMeasurements(
    PreparedMowingPlan plan,
    List<double> heights,
  ) async {
    if (heights.length != 3 ||
        heights.any(
          (height) => !height.isFinite || height < 0 || height > 1000,
        )) {
      errorMessage = 'Informe três alturas válidas entre 0 e 1000 cm.';
      notifyListeners();
      return false;
    }
    return _run(() async {
      if (!plan.canRunDemoRehearsal) {
        throw const MowingDemoNotEligibleError();
      }
      if (await vault.readPendingSyncBatch() != null) {
        throw const PendingBatchEditError();
      }
      final sourceOrders = orders.where(
        (order) => order.id == plan.sourceInspectionWorkOrderId,
      );
      if (sourceOrders.length != 1) {
        throw const MowingDemoSourcePointError();
      }
      final sourceOrder = sourceOrders.single;
      final events = await vault.readMowingLifecycleEvents(plan.id);
      if (!_isCompleteMowingDemoSequence(events) ||
          events.any(
            (event) =>
                event.mowingOrderId != plan.id ||
                event.sourcePlanningApprovalId != plan.planningApprovalId,
          )) {
        throw const MowingPostServiceNotReadyError();
      }
      final lifecycleStates = events.map((event) => event.syncState).toSet();
      if (lifecycleStates.length != 1 ||
          !const {
            DraftSyncState.localOnly,
            DraftSyncState.acknowledged,
          }.contains(lifecycleStates.single)) {
        throw const MowingPostServiceNotReadyError();
      }
      final existing = await vault.readMowingPostServiceMeasurements(plan.id);
      if (existing.any((item) => item.hasPersistentServerResult)) {
        throw const PersistedMowingPostServiceMeasurementEditError();
      }
      if (existing.any((item) => item.syncState == DraftSyncState.pending)) {
        throw const PendingBatchEditError();
      }
      final planningApprovalId = plan.planningApprovalId;
      if (planningApprovalId == null) {
        throw const MowingDemoNotEligibleError();
      }
      final capturedAt = _clock().toUtc();
      if (capturedAt.isBefore(events.last.occurredAt)) {
        throw const InvalidMowingPostServiceMeasurementTimeError();
      }
      final existingByPoint = {
        for (final item in existing) item.sourcePlannedPointId: item,
      };
      final measurements = List.generate(3, (index) {
        final point = sourceOrder.points[index];
        return MowingPostServiceMeasurementDraft(
          eventId: existingByPoint[point.id]?.eventId ?? _uuidFactory(),
          mowingOrderId: plan.id,
          sourcePlanningApprovalId: planningApprovalId,
          sourcePlannedPointId: point.id,
          sequence: point.sequence,
          heightCm: heights[index],
          capturedAt: capturedAt,
        );
      });
      await vault.replaceMowingPostServiceMeasurements(plan.id, measurements);
    });
  }

  Future<bool> syncMowingDemo(PreparedMowingPlan plan) async {
    final current = session;
    if (current == null) return false;
    return _run(() async {
      var events = await vault.readMowingLifecycleEvents(plan.id);
      var measurements = await vault.readMowingPostServiceMeasurements(plan.id);
      if (!_isCompleteMowingDemoSequence(events) ||
          events.any(
            (event) =>
                event.mowingOrderId != plan.id ||
                event.sourcePlanningApprovalId != plan.planningApprovalId,
          )) {
        throw const IncompleteMowingDemoLifecycleError();
      }
      final sourceOrders = orders.where(
        (order) => order.id == plan.sourceInspectionWorkOrderId,
      );
      if (sourceOrders.length != 1) {
        throw const MowingDemoSourcePointError();
      }
      final expectedPoints = {
        for (final point in sourceOrders.single.points) point.id,
      };
      if (measurements.length != 3 ||
          measurements.any(
            (item) =>
                item.mowingOrderId != plan.id ||
                item.sourcePlanningApprovalId != plan.planningApprovalId ||
                item.capturedAt.isBefore(events.last.occurredAt),
          ) ||
          measurements
                  .map((item) => item.sourcePlannedPointId)
                  .toSet()
                  .length !=
              3 ||
          !measurements
              .map((item) => item.sourcePlannedPointId)
              .toSet()
              .containsAll(expectedPoints)) {
        throw const IncompleteMowingPostServiceMeasurementError();
      }
      var pendingBatch = await vault.readPendingSyncBatch();
      if (pendingBatch == null) {
        final lifecycleStates = events.map((event) => event.syncState).toSet();
        if (lifecycleStates.length != 1 ||
            !const {
              DraftSyncState.localOnly,
              DraftSyncState.acknowledged,
            }.contains(lifecycleStates.single)) {
          throw const PersistedMowingDemoEditError();
        }
        if (measurements.any(
          (item) => item.syncState != DraftSyncState.localOnly,
        )) {
          throw const PersistedMowingPostServiceMeasurementEditError();
        }
        final localLifecycle = events
            .where((event) => event.syncState == DraftSyncState.localOnly)
            .toList(growable: false);
        pendingBatch = PendingSyncBatch(
          batchId: _uuidFactory(),
          deviceId: await deviceIdentityStore.readOrCreate(),
          orderId: plan.id,
          baseSyncCursor: await vault.readSyncCursor(),
          eventIds: [
            ...localLifecycle.map((event) => event.eventId),
            ...measurements.map((item) => item.eventId),
          ],
        );
        events = events
            .map(
              (event) => event.syncState == DraftSyncState.localOnly
                  ? event.copyWith(
                      syncState: DraftSyncState.pending,
                      clearResult: true,
                    )
                  : event,
            )
            .toList();
        measurements = measurements
            .map(
              (item) => item.copyWith(
                syncState: DraftSyncState.pending,
                clearResult: true,
              ),
            )
            .toList();
        await vault.savePendingMowingSyncBatch(
          pendingBatch,
          events,
          measurements,
        );
      } else if (pendingBatch.orderId != plan.id) {
        throw const AnotherOrderPendingError();
      }
      final pendingEventIds = {
        ...events
            .where((event) => event.syncState == DraftSyncState.pending)
            .map((event) => event.eventId),
        ...measurements
            .where((item) => item.syncState == DraftSyncState.pending)
            .map((item) => item.eventId),
      };
      if (pendingBatch.eventIds.length != pendingEventIds.length ||
          pendingBatch.eventIds.toSet().length != pendingEventIds.length ||
          !pendingEventIds.containsAll(pendingBatch.eventIds)) {
        throw const CorruptedPendingBatchError();
      }
      await gateway.registerDevice(
        current.accessToken,
        pendingBatch.deviceId,
        appVersion,
      );
      final result = await gateway
          .syncBatch(current.accessToken, pendingBatch, [
            ...events
                .where((event) => event.syncState == DraftSyncState.pending)
                .map((event) => event.toSyncEventJson()),
            ...measurements
                .where((item) => item.syncState == DraftSyncState.pending)
                .map((item) => item.toSyncEventJson()),
          ]);
      final coveredEventIds = {
        ...result.acceptedEventIds,
        ...result.rejectedEvents.keys,
        ...result.conflictingEvents.keys,
      };
      if (coveredEventIds.length != pendingBatch.eventIds.length ||
          !coveredEventIds.containsAll(pendingBatch.eventIds)) {
        throw const ZenitApiException(
          'A API não confirmou todos os eventos do lote.',
        );
      }
      await vault.completeMowingSyncBatch(
        plan.id,
        events
            .map(
              (event) => event.syncState == DraftSyncState.pending
                  ? _completeMowingLifecycleEvent(event, result)
                  : event,
            )
            .toList(),
        measurements
            .map(
              (item) => item.syncState == DraftSyncState.pending
                  ? _completeMowingPostServiceMeasurement(item, result)
                  : item,
            )
            .toList(),
        result.nextSyncCursor,
      );
    });
  }

  bool _isCompleteMowingDemoSequence(List<MowingDemoLifecycleEvent> events) {
    if (events.length < 3 ||
        events.first.operation != MowingDemoOperation.confirm ||
        events[1].operation != MowingDemoOperation.start ||
        events.last.operation != MowingDemoOperation.finish) {
      return false;
    }
    for (var index = 2; index < events.length - 1; index++) {
      final expected = index.isEven
          ? MowingDemoOperation.pause
          : MowingDemoOperation.resume;
      if (events[index].operation != expected) return false;
    }
    return events.length.isOdd;
  }

  MowingDemoLifecycleEvent _completeMowingLifecycleEvent(
    MowingDemoLifecycleEvent event,
    MobileSyncResult result,
  ) {
    if (result.acceptedEventIds.contains(event.eventId)) {
      return event.copyWith(
        syncState: DraftSyncState.acknowledged,
        syncResultCode: 'persisted',
        syncResultMessage: 'Ensaio simulado persistido.',
      );
    }
    final rejection = result.rejectedEvents[event.eventId];
    if (rejection != null) {
      return event.copyWith(
        syncState: DraftSyncState.rejected,
        syncResultCode: rejection.code,
        syncResultMessage: rejection.message,
      );
    }
    final conflict = result.conflictingEvents[event.eventId]!;
    return event.copyWith(
      syncState: DraftSyncState.conflict,
      syncResultCode: conflict.code,
      syncResultMessage: conflict.message,
    );
  }

  MowingPostServiceMeasurementDraft _completeMowingPostServiceMeasurement(
    MowingPostServiceMeasurementDraft measurement,
    MobileSyncResult result,
  ) {
    if (result.acceptedEventIds.contains(measurement.eventId)) {
      return measurement.copyWith(
        syncState: DraftSyncState.acknowledged,
        syncResultCode: 'persisted',
        syncResultMessage: 'Medição simulada e não verificada persistida.',
      );
    }
    final rejection = result.rejectedEvents[measurement.eventId];
    if (rejection != null) {
      return measurement.copyWith(
        syncState: DraftSyncState.rejected,
        syncResultCode: rejection.code,
        syncResultMessage: rejection.message,
      );
    }
    final conflict = result.conflictingEvents[measurement.eventId]!;
    return measurement.copyWith(
      syncState: DraftSyncState.conflict,
      syncResultCode: conflict.code,
      syncResultMessage: conflict.message,
    );
  }

  Future<bool> capturePreparedPhoto(
    PreparedWorkOrder order,
    PlannedInspectionPoint point,
  ) => _run(() async {
    final pendingBatch = await vault.readPendingSyncBatch();
    if (pendingBatch != null) throw const PendingBatchEditError();
    final lifecycle = await vault.readLifecycleEvents(order.id);
    if (lifecycle.length != 2 ||
        lifecycle.last.operation != DemoLifecycleOperation.start) {
      throw const DemoOrderNotStartedError();
    }
    final existing = await vault.readPhotoDrafts(order.id);
    final previous = existing
        .where((photo) => photo.plannedPointId == point.id)
        .firstOrNull;
    if (previous?.hasPersistentServerResult == true) {
      throw const PersistedPhotoEditError();
    }
    final captured = await _photoCapture.capture();
    if (captured == null) throw const PhotoCaptureCancelledError();
    final photo = PreparedPhotoDraft(
      eventId: _uuidFactory(),
      photoId: _uuidFactory(),
      orderId: order.id,
      plannedPointId: point.id,
      sequence: point.sequence,
      capturedAt: _clock().toUtc(),
      checksumSha256: captured.checksumSha256,
      mediaType: captured.mediaType,
      bytes: captured.bytes,
    );
    await vault.replacePhotoDrafts(
      order.id,
      [...existing.where((item) => item.plannedPointId != point.id), photo]
        ..sort((left, right) => left.sequence.compareTo(right.sequence)),
    );
  });

  Future<bool> confirmDemoOrder(PreparedWorkOrder order) => _run(() async {
    final events = await vault.readLifecycleEvents(order.id);
    if (events.isNotEmpty) throw const InvalidDemoLifecycleError();
    await vault.replaceLifecycleEvents(order.id, [
      DemoLifecycleEvent(
        eventId: _uuidFactory(),
        orderId: order.id,
        operation: DemoLifecycleOperation.confirm,
        occurredAt: _clock().toUtc(),
      ),
    ]);
  });

  Future<bool> startDemoOrder(PreparedWorkOrder order) => _run(() async {
    final events = await vault.readLifecycleEvents(order.id);
    if (events.length != 1 ||
        events.single.operation != DemoLifecycleOperation.confirm ||
        events.single.syncState != DraftSyncState.localOnly) {
      throw const InvalidDemoLifecycleError();
    }
    final demoPoint = order.points.first;
    await vault.replaceLifecycleEvents(order.id, [
      ...events,
      DemoLifecycleEvent(
        eventId: _uuidFactory(),
        orderId: order.id,
        operation: DemoLifecycleOperation.start,
        occurredAt: _clock().toUtc(),
        simulatedLatitude: demoPoint.latitude,
        simulatedLongitude: demoPoint.longitude,
      ),
    ]);
  });

  Future<bool> finishDemoOrder(PreparedWorkOrder order) => _run(() async {
    final events = await vault.readLifecycleEvents(order.id);
    final drafts = await vault.readDrafts(order.id);
    final photos = await vault.readPhotoDrafts(order.id);
    if (events.length != 2 ||
        events[0].operation != DemoLifecycleOperation.confirm ||
        events[1].operation != DemoLifecycleOperation.start ||
        drafts.length != 3 ||
        events.any((event) => event.syncState != DraftSyncState.localOnly)) {
      throw const InvalidDemoLifecycleError();
    }
    if (photos.length != 3 ||
        photos.map((photo) => photo.plannedPointId).toSet().length != 3) {
      throw const IncompletePhotoBatchError();
    }
    await vault.replaceLifecycleEvents(order.id, [
      ...events,
      DemoLifecycleEvent(
        eventId: _uuidFactory(),
        orderId: order.id,
        operation: DemoLifecycleOperation.finish,
        occurredAt: _clock().toUtc(),
      ),
    ]);
  });

  Future<bool> saveThreeDrafts(
    PreparedWorkOrder order,
    List<double> heights,
  ) async {
    if (heights.length != 3 ||
        heights.any((height) => height < 0 || height > 1000)) {
      errorMessage = 'Informe três alturas válidas entre 0 e 1000 cm.';
      notifyListeners();
      return false;
    }
    if (order.authorizesFieldWork || order.eligibleForFieldExecution) {
      errorMessage =
          'Esta versão aceita apenas ordens preparadas e não operacionais.';
      notifyListeners();
      return false;
    }
    return _run(() async {
      final pendingBatch = await vault.readPendingSyncBatch();
      if (pendingBatch != null) throw const PendingBatchEditError();
      final existing = await vault.readDrafts(order.id);
      if (existing.any((draft) => draft.hasPersistentServerResult)) {
        throw const PersistedDraftEditError();
      }
      if (existing.any((draft) => draft.syncState == DraftSyncState.pending)) {
        throw const PendingBatchEditError();
      }
      final lifecycle = await vault.readLifecycleEvents(order.id);
      if (lifecycle.length != 2 ||
          lifecycle.last.operation != DemoLifecycleOperation.start) {
        throw const DemoOrderNotStartedError();
      }
      final existingByPoint = {
        for (final draft in existing) draft.plannedPointId: draft,
      };
      final recordedAt = _clock().toUtc();
      final drafts = List.generate(3, (index) {
        final point = order.points[index];
        return MeasurementDraft(
          eventId: existingByPoint[point.id]?.eventId ?? _uuidFactory(),
          orderId: order.id,
          plannedPointId: point.id,
          sequence: point.sequence,
          heightCm: heights[index],
          recordedAt: recordedAt,
        );
      });
      await vault.replaceDrafts(order.id, drafts);
    });
  }

  Future<bool> syncPreparedDrafts(PreparedWorkOrder order) async {
    final current = session;
    if (current == null) return false;
    return _run(() async {
      var drafts = await vault.readDrafts(order.id);
      var lifecycle = await vault.readLifecycleEvents(order.id);
      var photos = await vault.readPhotoDrafts(order.id);
      final expectedPoints = {for (final point in order.points) point.id};
      if (drafts.length != 3 ||
          drafts.any((draft) => draft.orderId != order.id) ||
          drafts.map((draft) => draft.plannedPointId).toSet().length != 3 ||
          !drafts
              .map((draft) => draft.plannedPointId)
              .toSet()
              .containsAll(expectedPoints)) {
        throw const IncompleteDraftBatchError();
      }
      if (lifecycle.length != 3 ||
          lifecycle[0].operation != DemoLifecycleOperation.confirm ||
          lifecycle[1].operation != DemoLifecycleOperation.start ||
          lifecycle[2].operation != DemoLifecycleOperation.finish) {
        throw const IncompleteDemoLifecycleError();
      }
      if (photos.length != 3 ||
          photos.any((photo) => photo.orderId != order.id) ||
          photos.map((photo) => photo.plannedPointId).toSet().length != 3 ||
          !photos
              .map((photo) => photo.plannedPointId)
              .toSet()
              .containsAll(expectedPoints)) {
        throw const IncompletePhotoBatchError();
      }

      var pendingBatch = await vault.readPendingSyncBatch();
      if (pendingBatch == null) {
        if (drafts.any(
              (draft) => draft.syncState != DraftSyncState.localOnly,
            ) ||
            lifecycle.any(
              (event) => event.syncState != DraftSyncState.localOnly,
            ) ||
            photos.any(
              (photo) => photo.syncState != DraftSyncState.localOnly,
            )) {
          throw const PersistedDraftEditError();
        }
        final deviceId = await deviceIdentityStore.readOrCreate();
        pendingBatch = PendingSyncBatch(
          batchId: _uuidFactory(),
          deviceId: deviceId,
          orderId: order.id,
          baseSyncCursor: await vault.readSyncCursor(),
          eventIds: [
            lifecycle[0].eventId,
            lifecycle[1].eventId,
            for (var index = 0; index < 3; index++) ...[
              drafts[index].eventId,
              photos[index].eventId,
            ],
            lifecycle[2].eventId,
          ],
        );
        drafts = drafts
            .map(
              (draft) => draft.copyWith(
                syncState: DraftSyncState.pending,
                clearResult: true,
              ),
            )
            .toList();
        lifecycle = lifecycle
            .map(
              (event) => event.copyWith(
                syncState: DraftSyncState.pending,
                clearResult: true,
              ),
            )
            .toList();
        photos = photos
            .map(
              (photo) => photo.copyWith(
                syncState: DraftSyncState.pending,
                clearResult: true,
              ),
            )
            .toList();
        await vault.savePendingSyncBatch(
          pendingBatch,
          drafts,
          lifecycle,
          photos,
        );
      } else if (pendingBatch.orderId != order.id) {
        throw const AnotherOrderPendingError();
      }
      final localEventIds = {
        ...drafts.map((draft) => draft.eventId),
        ...lifecycle.map((event) => event.eventId),
        ...photos.map((photo) => photo.eventId),
      };
      if (pendingBatch.eventIds.length != localEventIds.length ||
          pendingBatch.eventIds.toSet().length != localEventIds.length ||
          !localEventIds.containsAll(pendingBatch.eventIds)) {
        throw const CorruptedPendingBatchError();
      }

      await gateway.registerDevice(
        current.accessToken,
        pendingBatch.deviceId,
        appVersion,
      );
      final result = await gateway.syncBatch(
        current.accessToken,
        pendingBatch,
        [
          lifecycle[0].toSyncEventJson(),
          lifecycle[1].toSyncEventJson(),
          for (var index = 0; index < 3; index++) ...[
            drafts[index].toSyncEventJson(),
            photos[index].toSyncEventJson(),
          ],
          lifecycle[2].toSyncEventJson(),
        ],
      );
      final coveredEventIds = {
        ...result.acceptedEventIds,
        ...result.rejectedEvents.keys,
        ...result.conflictingEvents.keys,
      };
      if (coveredEventIds.length != pendingBatch.eventIds.length ||
          !coveredEventIds.containsAll(pendingBatch.eventIds)) {
        throw const ZenitApiException(
          'A API não confirmou todos os eventos do lote.',
        );
      }

      final completed = drafts.map((draft) {
        if (result.acceptedEventIds.contains(draft.eventId)) {
          return draft.copyWith(
            syncState: DraftSyncState.acknowledged,
            syncResultCode: 'persisted',
            syncResultMessage: 'Confirmação persistente recebida.',
          );
        }
        final rejection = result.rejectedEvents[draft.eventId];
        if (rejection != null) {
          return draft.copyWith(
            syncState: DraftSyncState.rejected,
            syncResultCode: rejection.code,
            syncResultMessage: rejection.message,
          );
        }
        final conflict = result.conflictingEvents[draft.eventId]!;
        return draft.copyWith(
          syncState: DraftSyncState.conflict,
          syncResultCode: conflict.code,
          syncResultMessage: conflict.message,
        );
      }).toList();
      final completedLifecycle = lifecycle
          .map((event) => _completeLifecycleEvent(event, result))
          .toList();
      final completedPhotos = photos
          .map((photo) => _completePhoto(photo, result))
          .toList();
      await vault.completeSyncBatch(
        order.id,
        completed,
        completedLifecycle,
        completedPhotos,
        result.nextSyncCursor,
      );
    });
  }

  DemoLifecycleEvent _completeLifecycleEvent(
    DemoLifecycleEvent event,
    MobileSyncResult result,
  ) {
    if (result.acceptedEventIds.contains(event.eventId)) {
      return event.copyWith(
        syncState: DraftSyncState.acknowledged,
        syncResultCode: 'persisted',
        syncResultMessage: 'Confirmação persistente recebida.',
      );
    }
    final rejection = result.rejectedEvents[event.eventId];
    if (rejection != null) {
      return event.copyWith(
        syncState: DraftSyncState.rejected,
        syncResultCode: rejection.code,
        syncResultMessage: rejection.message,
      );
    }
    final conflict = result.conflictingEvents[event.eventId]!;
    return event.copyWith(
      syncState: DraftSyncState.conflict,
      syncResultCode: conflict.code,
      syncResultMessage: conflict.message,
    );
  }

  PreparedPhotoDraft _completePhoto(
    PreparedPhotoDraft photo,
    MobileSyncResult result,
  ) {
    if (result.acceptedEventIds.contains(photo.eventId)) {
      return photo.copyWith(
        syncState: DraftSyncState.acknowledged,
        syncResultCode: 'persisted',
        syncResultMessage: 'Manifesto persistido; conteúdo não enviado.',
      );
    }
    final rejection = result.rejectedEvents[photo.eventId];
    if (rejection != null) {
      return photo.copyWith(
        syncState: DraftSyncState.rejected,
        syncResultCode: rejection.code,
        syncResultMessage: rejection.message,
      );
    }
    final conflict = result.conflictingEvents[photo.eventId]!;
    return photo.copyWith(
      syncState: DraftSyncState.conflict,
      syncResultCode: conflict.code,
      syncResultMessage: conflict.message,
    );
  }

  Future<bool> uploadPreparedPhotos(PreparedWorkOrder order) async {
    final current = session;
    if (current == null) return false;
    return _run(() async {
      var photos = await vault.readPhotoDrafts(order.id);
      if (photos.length != 3 ||
          photos.any(
            (photo) => photo.syncState != DraftSyncState.acknowledged,
          )) {
        throw const IncompletePhotoBatchError();
      }
      final deviceId = await deviceIdentityStore.readOrCreate();
      await gateway.registerDevice(current.accessToken, deviceId, appVersion);
      for (var index = 0; index < photos.length; index++) {
        final photo = photos[index];
        if (photo.isUploaded) continue;
        await gateway.uploadPreparedPhoto(current.accessToken, deviceId, photo);
        photos = [...photos]
          ..[index] = photo.copyWith(
            uploadState: PhotoUploadState.uploadedUnverified,
            syncResultMessage:
                'Conteúdo recebido e criptografado; qualidade e régua não validadas.',
          );
        await vault.replacePhotoDrafts(order.id, photos);
      }
    });
  }

  Future<bool> _run(Future<void> Function() action) async {
    busy = true;
    errorMessage = null;
    notifyListeners();
    try {
      await action();
      return true;
    } catch (error) {
      if (error is ZenitApiException && error.statusCode == 401) {
        await _invalidateSession();
      }
      errorMessage = error is ZenitApiException
          ? error.message
          : error is MobileWorkflowException
          ? error.message
          : 'Operação não concluída: $error';
      return false;
    } finally {
      busy = false;
      notifyListeners();
    }
  }
}

sealed class MobileWorkflowException implements Exception {
  const MobileWorkflowException(this.message);
  final String message;
}

class LocalPendingEventsError extends MobileWorkflowException {
  const LocalPendingEventsError()
    : super('Há eventos não confirmados de outro usuário neste aparelho.');
}

class PendingBatchEditError extends MobileWorkflowException {
  const PendingBatchEditError()
    : super('Um lote já foi preparado; sincronize-o antes de editar.');
}

class PersistedDraftEditError extends MobileWorkflowException {
  const PersistedDraftEditError()
    : super(
        'A medição já recebeu resultado persistente e não pode ser sobrescrita.',
      );
}

class IncompleteDraftBatchError extends MobileWorkflowException {
  const IncompleteDraftBatchError()
    : super('Salve exatamente três medições antes de sincronizar.');
}

class AnotherOrderPendingError extends MobileWorkflowException {
  const AnotherOrderPendingError()
    : super('Existe um lote pendente de outra ordem neste aparelho.');
}

class CorruptedPendingBatchError extends MobileWorkflowException {
  const CorruptedPendingBatchError()
    : super('O lote pendente não corresponde às medições locais.');
}

class InvalidDemoLifecycleError extends MobileWorkflowException {
  const InvalidDemoLifecycleError()
    : super(
        'A sequência demonstrativa deve ser confirmar, iniciar e finalizar.',
      );
}

class DemoOrderNotStartedError extends MobileWorkflowException {
  const DemoOrderNotStartedError()
    : super('Confirme e inicie a demonstração antes das medições.');
}

class IncompleteDemoLifecycleError extends MobileWorkflowException {
  const IncompleteDemoLifecycleError()
    : super('Finalize a demonstração antes de sincronizar.');
}

class PersistedPhotoEditError extends MobileWorkflowException {
  const PersistedPhotoEditError()
    : super(
        'O manifesto da foto já foi persistido e não pode ser substituído.',
      );
}

class PhotoCaptureCancelledError extends MobileWorkflowException {
  const PhotoCaptureCancelledError() : super('Captura de foto cancelada.');
}

class IncompletePhotoBatchError extends MobileWorkflowException {
  const IncompletePhotoBatchError()
    : super('Capture uma foto preparada em cada um dos três pontos.');
}

class MowingDemoNotEligibleError extends MobileWorkflowException {
  const MowingDemoNotEligibleError()
    : super(
        'O ensaio exige planejamento efetivo e declarações preparadas de clima e segurança livres.',
      );
}

class MowingDemoSourcePointError extends MobileWorkflowException {
  const MowingDemoSourcePointError()
    : super(
        'O ponto estimado da inspeção de origem não está disponível neste aparelho.',
      );
}

class InvalidMowingDemoLifecycleError extends MobileWorkflowException {
  const InvalidMowingDemoLifecycleError()
    : super(
        'Use confirmar, iniciar, pausar/retomar em pares e finalizar o ensaio.',
      );
}

class IncompleteMowingDemoLifecycleError extends MobileWorkflowException {
  const IncompleteMowingDemoLifecycleError()
    : super('Finalize uma sequência válida antes de sincronizar o ensaio.');
}

class PersistedMowingDemoEditError extends MobileWorkflowException {
  const PersistedMowingDemoEditError()
    : super('Um evento do ensaio já tem resultado persistente e é imutável.');
}

class InvalidMowingDemoTimeError extends MobileWorkflowException {
  const InvalidMowingDemoTimeError()
    : super('O relógio do aparelho retrocedeu durante o ensaio.');
}

class MowingPostServiceNotReadyError extends MobileWorkflowException {
  const MowingPostServiceNotReadyError()
    : super(
        'Finalize um ensaio local válido ou confirmado antes das medições pós-serviço.',
      );
}

class IncompleteMowingPostServiceMeasurementError
    extends MobileWorkflowException {
  const IncompleteMowingPostServiceMeasurementError()
    : super(
        'Salve uma medição pós-serviço simulada para cada um dos três pontos.',
      );
}

class PersistedMowingPostServiceMeasurementEditError
    extends MobileWorkflowException {
  const PersistedMowingPostServiceMeasurementEditError()
    : super('A medição pós-serviço já tem resultado persistente e é imutável.');
}

class InvalidMowingPostServiceMeasurementTimeError
    extends MobileWorkflowException {
  const InvalidMowingPostServiceMeasurementTimeError()
    : super('A medição pós-serviço não pode ser anterior ao fim do ensaio.');
}
