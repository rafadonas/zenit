part of '../../../app_controller.dart';

extension InspectionWorkflowController on ZenitAppController {
  Future<List<MeasurementDraft>> readDrafts(String orderId) =>
      vault.readDrafts(orderId);

  Future<List<DemoLifecycleEvent>> readLifecycleEvents(String orderId) =>
      vault.readLifecycleEvents(orderId);

  Future<List<PreparedPhotoDraft>> readPhotoDrafts(String orderId) =>
      vault.readPhotoDrafts(orderId);

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
      _notifyWorkflowListeners();
      return false;
    }
    if (order.authorizesFieldWork || order.eligibleForFieldExecution) {
      errorMessage =
          'Esta versão aceita apenas ordens preparadas e não operacionais.';
      _notifyWorkflowListeners();
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
}
