import 'package:flutter/foundation.dart';

import 'data/offline_vault.dart';
import 'data/device_identity_store.dart';
import 'data/secure_session_store.dart';
import 'data/zenit_gateway.dart';
import 'domain/auth_session.dart';
import 'domain/measurement_draft.dart';
import 'domain/mobile_sync.dart';
import 'domain/prepared_work_order.dart';

class ZenitAppController extends ChangeNotifier {
  ZenitAppController({
    required this.gateway,
    required this.sessionStore,
    required this.vault,
    required this.deviceIdentityStore,
    required this.appVersion,
    DateTime Function()? clock,
    String Function()? uuidFactory,
  }) : _clock = clock ?? DateTime.now,
       _uuidFactory = uuidFactory ?? generateUuidV4;

  final ZenitGateway gateway;
  final SessionStore sessionStore;
  final OfflineVault vault;
  final DeviceIdentityStore deviceIdentityStore;
  final String appVersion;
  final DateTime Function() _clock;
  final String Function() _uuidFactory;

  AuthSession? session;
  List<PreparedWorkOrder> orders = const [];
  bool initializing = true;
  bool busy = false;
  String? errorMessage;

  bool get isAuthenticated => session != null;

  Future<void> initialize() async {
    try {
      await vault.initialize();
      orders = await vault.readOrders();
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
      final downloaded = await gateway.listPreparedOrders(
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
      await vault.replaceOrders(downloaded);
      await sessionStore.write(authenticated);
      session = authenticated;
      orders = downloaded;
    });
  }

  Future<bool> refreshOrders({bool silent = false}) async {
    final current = session;
    if (current == null) return false;
    if (silent) {
      try {
        final downloaded = await gateway.listPreparedOrders(
          current.accessToken,
        );
        await vault.replaceOrders(downloaded);
        orders = downloaded;
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
      final downloaded = await gateway.listPreparedOrders(current.accessToken);
      await vault.replaceOrders(downloaded);
      orders = downloaded;
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
  }

  Future<List<MeasurementDraft>> readDrafts(String orderId) =>
      vault.readDrafts(orderId);

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

      var pendingBatch = await vault.readPendingSyncBatch();
      if (pendingBatch == null) {
        if (drafts.any(
          (draft) => draft.syncState != DraftSyncState.localOnly,
        )) {
          throw const PersistedDraftEditError();
        }
        final deviceId = await deviceIdentityStore.readOrCreate();
        pendingBatch = PendingSyncBatch(
          batchId: _uuidFactory(),
          deviceId: deviceId,
          orderId: order.id,
          baseSyncCursor: await vault.readSyncCursor(),
          eventIds: drafts.map((draft) => draft.eventId).toList(),
        );
        drafts = drafts
            .map(
              (draft) => draft.copyWith(
                syncState: DraftSyncState.pending,
                clearResult: true,
              ),
            )
            .toList();
        await vault.savePendingSyncBatch(pendingBatch, drafts);
      } else if (pendingBatch.orderId != order.id) {
        throw const AnotherOrderPendingError();
      }
      final localEventIds = drafts.map((draft) => draft.eventId).toSet();
      if (pendingBatch.eventIds.length != drafts.length ||
          pendingBatch.eventIds.toSet().length != drafts.length ||
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
        drafts,
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
      await vault.completeSyncBatch(order.id, completed, result.nextSyncCursor);
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
