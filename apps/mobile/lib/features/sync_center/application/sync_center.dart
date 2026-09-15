part of '../../../app_controller.dart';

extension SyncCenterController on ZenitAppController {
  Future<List<SyncCenterItem>> readSyncCenterItems() async {
    final attempts = await vault.readSyncAttempts();
    final items = <SyncCenterItem>[];

    for (final order in orders) {
      final lifecycle = await vault.readLifecycleEvents(order.id);
      final drafts = await vault.readDrafts(order.id);
      final photos = await vault.readPhotoDrafts(order.id);
      final states = [
        ...lifecycle.map((event) => event.syncState),
        ...drafts.map((draft) => draft.syncState),
        ...photos.map((photo) => photo.syncState),
      ];
      if (states.isNotEmpty) {
        final key = syncWorkItemKey(SyncWorkKind.inspectionBatch, order.id);
        items.add(
          _syncCenterItem(
            attempts: attempts,
            key: key,
            sourceId: order.id,
            kind: SyncWorkKind.inspectionBatch,
            title: '${order.roadCode} · inspeção ${order.segmentIndex}',
            subtitle:
                '${states.length} eventos/manifestos · lote preparado e idempotente',
            status: _aggregateSyncStates(states),
            canRetry:
                lifecycle.length == 3 &&
                drafts.length == 3 &&
                photos.length == 3 &&
                !states.any(
                  (state) =>
                      state == DraftSyncState.rejected ||
                      state == DraftSyncState.conflict,
                ) &&
                states.any(
                  (state) =>
                      state == DraftSyncState.localOnly ||
                      state == DraftSyncState.pending,
                ),
          ),
        );
      }
      if (photos.isNotEmpty) {
        final key = syncWorkItemKey(
          SyncWorkKind.inspectionPhotoUpload,
          order.id,
        );
        final manifestsAccepted =
            photos.length == 3 &&
            photos.every(
              (photo) => photo.syncState == DraftSyncState.acknowledged,
            );
        final uploaded = photos.where((photo) => photo.isUploaded).length;
        items.add(
          _syncCenterItem(
            attempts: attempts,
            key: key,
            sourceId: order.id,
            kind: SyncWorkKind.inspectionPhotoUpload,
            title: '${order.roadCode} · fotos da inspeção',
            subtitle: manifestsAccepted
                ? '$uploaded/3 conteúdos recebidos; qualidade não validada'
                : 'Aguardando aceite dos 3 manifestos antes dos bytes',
            status: uploaded == 3
                ? SyncCenterStatus.accepted
                : _aggregateSyncStates(photos.map((photo) => photo.syncState)),
            canRetry: manifestsAccepted && uploaded < 3,
          ),
        );
      }
    }

    for (final plan in mowingPlans) {
      final lifecycle = await vault.readMowingLifecycleEvents(plan.id);
      final measurements = await vault.readMowingPostServiceMeasurements(
        plan.id,
      );
      final photos = await vault.readMowingPostServicePhotos(plan.id);
      final states = [
        ...lifecycle.map((event) => event.syncState),
        ...measurements.map((item) => item.syncState),
        ...photos.map((photo) => photo.syncState),
      ];
      if (states.isNotEmpty) {
        final key = syncWorkItemKey(SyncWorkKind.mowingBatch, plan.id);
        items.add(
          _syncCenterItem(
            attempts: attempts,
            key: key,
            sourceId: plan.id,
            kind: SyncWorkKind.mowingBatch,
            title: '${plan.roadCode} · ensaio ${plan.segmentIndex}',
            subtitle:
                '${states.length} eventos/manifestos simulados · não operacional',
            status: _aggregateSyncStates(states),
            canRetry:
                lifecycle.length >= 3 &&
                measurements.length == 3 &&
                photos.length == 3 &&
                !states.any(
                  (state) =>
                      state == DraftSyncState.rejected ||
                      state == DraftSyncState.conflict,
                ) &&
                states.any(
                  (state) =>
                      state == DraftSyncState.localOnly ||
                      state == DraftSyncState.pending,
                ),
          ),
        );
      }
      if (photos.isNotEmpty) {
        final key = syncWorkItemKey(SyncWorkKind.mowingPhotoUpload, plan.id);
        final manifestsAccepted =
            photos.length == 3 &&
            photos.every(
              (photo) => photo.syncState == DraftSyncState.acknowledged,
            );
        final uploaded = photos.where((photo) => photo.isUploaded).length;
        items.add(
          _syncCenterItem(
            attempts: attempts,
            key: key,
            sourceId: plan.id,
            kind: SyncWorkKind.mowingPhotoUpload,
            title: '${plan.roadCode} · fotos pós-serviço',
            subtitle: manifestsAccepted
                ? '$uploaded/3 conteúdos simulados recebidos; não validados'
                : 'Aguardando aceite dos 3 manifestos antes dos bytes',
            status: uploaded == 3
                ? SyncCenterStatus.accepted
                : _aggregateSyncStates(photos.map((photo) => photo.syncState)),
            canRetry: manifestsAccepted && uploaded < 3,
          ),
        );
      }
    }
    return items;
  }

  Future<bool> retrySyncCenterItem(SyncCenterItem item) async {
    switch (item.kind) {
      case SyncWorkKind.inspectionBatch:
        return syncPreparedDrafts(
          orders.singleWhere((order) => order.id == item.sourceId),
        );
      case SyncWorkKind.inspectionPhotoUpload:
        return uploadPreparedPhotos(
          orders.singleWhere((order) => order.id == item.sourceId),
        );
      case SyncWorkKind.mowingBatch:
        return syncMowingDemo(
          mowingPlans.singleWhere((plan) => plan.id == item.sourceId),
        );
      case SyncWorkKind.mowingPhotoUpload:
        return uploadMowingPostServicePhotos(
          mowingPlans.singleWhere((plan) => plan.id == item.sourceId),
        );
    }
  }

  SyncCenterItem _syncCenterItem({
    required Map<String, SyncAttemptRecord> attempts,
    required String key,
    required String sourceId,
    required SyncWorkKind kind,
    required String title,
    required String subtitle,
    required SyncCenterStatus status,
    required bool canRetry,
  }) {
    final attempt = attempts[key];
    return SyncCenterItem(
      key: key,
      sourceId: sourceId,
      kind: kind,
      title: title,
      subtitle: subtitle,
      status: activeSyncItemKey == key ? SyncCenterStatus.sending : status,
      canRetry: canRetry && activeSyncItemKey == null,
      attemptCount: attempt?.attemptCount ?? 0,
      lastAttemptAt: attempt?.lastAttemptAt,
    );
  }
}

SyncCenterStatus _aggregateSyncStates(Iterable<DraftSyncState> states) {
  final values = states.toList();
  if (values.any((state) => state == DraftSyncState.conflict)) {
    return SyncCenterStatus.conflict;
  }
  if (values.any((state) => state == DraftSyncState.rejected)) {
    return SyncCenterStatus.rejected;
  }
  if (values.isNotEmpty &&
      values.every((state) => state == DraftSyncState.acknowledged)) {
    return SyncCenterStatus.accepted;
  }
  return SyncCenterStatus.pending;
}
