part of '../../../app_controller.dart';

extension MowingRehearsalWorkflowController on ZenitAppController {
  Future<List<MowingDemoLifecycleEvent>> readMowingLifecycleEvents(
    String mowingOrderId,
  ) => vault.readMowingLifecycleEvents(mowingOrderId);

  Future<List<MowingPostServiceMeasurementDraft>>
  readMowingPostServiceMeasurements(String mowingOrderId) =>
      vault.readMowingPostServiceMeasurements(mowingOrderId);

  Future<List<MowingPostServicePhotoDraft>> readMowingPostServicePhotos(
    String mowingOrderId,
  ) => vault.readMowingPostServicePhotos(mowingOrderId);

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
      _notifyWorkflowListeners();
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
      if ((await vault.readMowingPostServicePhotos(plan.id)).isNotEmpty) {
        throw const MowingPostServiceMeasurementHasPhotoError();
      }
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

  Future<bool> captureMowingPostServicePhoto(
    PreparedMowingPlan plan,
    PlannedInspectionPoint point,
  ) => _run(() async {
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
    final matchingPoints = sourceOrders.single.points.where(
      (candidate) => candidate.id == point.id,
    );
    if (matchingPoints.length != 1) {
      throw const MowingDemoSourcePointError();
    }
    final sourcePoint = matchingPoints.single;
    final events = await vault.readMowingLifecycleEvents(plan.id);
    if (!_isCompleteMowingDemoSequence(events) ||
        events.any(
          (event) =>
              event.mowingOrderId != plan.id ||
              event.sourcePlanningApprovalId != plan.planningApprovalId ||
              !const {
                DraftSyncState.localOnly,
                DraftSyncState.acknowledged,
              }.contains(event.syncState),
        )) {
      throw const MowingPostServicePhotoNotReadyError();
    }
    final measurements = await vault.readMowingPostServiceMeasurements(plan.id);
    final matchingMeasurements = measurements.where(
      (measurement) =>
          measurement.sourcePlannedPointId == point.id &&
          measurement.mowingOrderId == plan.id &&
          measurement.sourcePlanningApprovalId == plan.planningApprovalId,
    );
    if (matchingMeasurements.length != 1 ||
        !const {
          DraftSyncState.localOnly,
          DraftSyncState.acknowledged,
        }.contains(matchingMeasurements.single.syncState)) {
      throw const MowingPostServicePhotoNotReadyError();
    }
    final existing = await vault.readMowingPostServicePhotos(plan.id);
    final previous = existing
        .where((photo) => photo.sourcePlannedPointId == point.id)
        .firstOrNull;
    if (previous?.hasPersistentServerResult == true) {
      throw const PersistedMowingPostServicePhotoEditError();
    }
    final captured = await _photoCapture.capture();
    if (captured == null) throw const PhotoCaptureCancelledError();
    final capturedAt = _clock().toUtc();
    if (capturedAt.isBefore(matchingMeasurements.single.capturedAt)) {
      throw const InvalidMowingPostServicePhotoTimeError();
    }
    final planningApprovalId = plan.planningApprovalId;
    if (planningApprovalId == null) {
      throw const MowingDemoNotEligibleError();
    }
    final photo = MowingPostServicePhotoDraft(
      eventId: _uuidFactory(),
      photoId: _uuidFactory(),
      mowingOrderId: plan.id,
      sourcePlanningApprovalId: planningApprovalId,
      sourcePlannedPointId: sourcePoint.id,
      sequence: sourcePoint.sequence,
      capturedAt: capturedAt,
      checksumSha256: captured.checksumSha256,
      mediaType: captured.mediaType,
      bytes: captured.bytes,
    );
    await vault.replaceMowingPostServicePhotos(
      plan.id,
      [
        ...existing.where((item) => item.sourcePlannedPointId != point.id),
        photo,
      ]..sort((left, right) => left.sequence.compareTo(right.sequence)),
    );
  });

  Future<bool> syncMowingDemo(PreparedMowingPlan plan) async {
    final current = session;
    if (current == null) return false;
    return _run(() async {
      var events = await vault.readMowingLifecycleEvents(plan.id);
      var measurements = await vault.readMowingPostServiceMeasurements(plan.id);
      var photos = await vault.readMowingPostServicePhotos(plan.id);
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
      final measurementsByPoint = {
        for (final measurement in measurements)
          measurement.sourcePlannedPointId: measurement,
      };
      if (photos.length != 3 ||
          photos.any(
            (photo) =>
                photo.mowingOrderId != plan.id ||
                photo.sourcePlanningApprovalId != plan.planningApprovalId ||
                !expectedPoints.contains(photo.sourcePlannedPointId) ||
                photo.sequence !=
                    measurementsByPoint[photo.sourcePlannedPointId]!.sequence ||
                photo.capturedAt.isBefore(
                  measurementsByPoint[photo.sourcePlannedPointId]!.capturedAt,
                ),
          ) ||
          photos.map((photo) => photo.sourcePlannedPointId).toSet().length !=
              3) {
        throw const IncompleteMowingPostServicePhotoError();
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
        final measurementStates = measurements
            .map((item) => item.syncState)
            .toSet();
        if (measurementStates.length != 1 ||
            !const {
              DraftSyncState.localOnly,
              DraftSyncState.acknowledged,
            }.contains(measurementStates.single)) {
          throw const PersistedMowingPostServiceMeasurementEditError();
        }
        if (photos.any(
          (photo) => photo.syncState != DraftSyncState.localOnly,
        )) {
          throw const PersistedMowingPostServicePhotoEditError();
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
            for (final measurement in measurements) ...[
              if (measurement.syncState == DraftSyncState.localOnly)
                measurement.eventId,
              photos
                  .singleWhere(
                    (photo) =>
                        photo.sourcePlannedPointId ==
                        measurement.sourcePlannedPointId,
                  )
                  .eventId,
            ],
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
              (item) => item.syncState == DraftSyncState.localOnly
                  ? item.copyWith(
                      syncState: DraftSyncState.pending,
                      clearResult: true,
                    )
                  : item,
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
        await vault.savePendingMowingSyncBatch(
          pendingBatch,
          events,
          measurements,
          photos,
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
        ...photos
            .where((photo) => photo.syncState == DraftSyncState.pending)
            .map((photo) => photo.eventId),
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
      final result = await gateway.syncBatch(
        current.accessToken,
        pendingBatch,
        [
          ...events
              .where((event) => event.syncState == DraftSyncState.pending)
              .map((event) => event.toSyncEventJson()),
          for (final measurement in measurements) ...[
            if (measurement.syncState == DraftSyncState.pending)
              measurement.toSyncEventJson(),
            ...photos
                .where(
                  (photo) =>
                      photo.syncState == DraftSyncState.pending &&
                      photo.sourcePlannedPointId ==
                          measurement.sourcePlannedPointId,
                )
                .map((photo) => photo.toSyncEventJson()),
          ],
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
        photos
            .map(
              (photo) => photo.syncState == DraftSyncState.pending
                  ? _completeMowingPostServicePhoto(photo, result)
                  : photo,
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

  MowingPostServicePhotoDraft _completeMowingPostServicePhoto(
    MowingPostServicePhotoDraft photo,
    MobileSyncResult result,
  ) {
    if (result.acceptedEventIds.contains(photo.eventId)) {
      return photo.copyWith(
        syncState: DraftSyncState.acknowledged,
        syncResultCode: 'persisted',
        syncResultMessage:
            'Manifesto persistido; conteúdo criptografado ainda não enviado.',
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

  Future<bool> uploadMowingPostServicePhotos(PreparedMowingPlan plan) async {
    final current = session;
    if (current == null) return false;
    return _run(() async {
      var photos = await vault.readMowingPostServicePhotos(plan.id);
      final sourceOrders = orders.where(
        (order) => order.id == plan.sourceInspectionWorkOrderId,
      );
      if (sourceOrders.length != 1) {
        throw const MowingDemoSourcePointError();
      }
      final expectedPoints = {
        for (final point in sourceOrders.single.points) point.id,
      };
      if (photos.length != 3 ||
          photos.any(
            (photo) =>
                photo.mowingOrderId != plan.id ||
                photo.sourcePlanningApprovalId != plan.planningApprovalId ||
                photo.syncState != DraftSyncState.acknowledged,
          ) ||
          photos.map((photo) => photo.sourcePlannedPointId).toSet().length !=
              3 ||
          !photos
              .map((photo) => photo.sourcePlannedPointId)
              .toSet()
              .containsAll(expectedPoints)) {
        throw const IncompleteMowingPostServicePhotoError();
      }
      final deviceId = await deviceIdentityStore.readOrCreate();
      await gateway.registerDevice(current.accessToken, deviceId, appVersion);
      for (var index = 0; index < photos.length; index++) {
        final photo = photos[index];
        if (photo.isUploaded) continue;
        await gateway.uploadMowingPostServicePhoto(
          current.accessToken,
          deviceId,
          photo,
        );
        photos = [...photos]
          ..[index] = photo.copyWith(
            uploadState: MowingPhotoUploadState.uploadedUnverified,
            syncResultMessage:
                'Conteúdo simulado recebido e criptografado; localização, qualidade e régua não validadas.',
          );
        await vault.replaceMowingPostServicePhotos(plan.id, photos);
      }
    });
  }
}
