import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';

import '../domain/measurement_draft.dart';
import '../domain/mobile_sync.dart';
import '../domain/prepared_work_order.dart';

abstract interface class OfflineVault {
  Future<void> initialize();
  Future<List<PreparedWorkOrder>> readOrders();
  Future<void> replaceOrders(List<PreparedWorkOrder> orders);
  Future<List<MeasurementDraft>> readDrafts(String orderId);
  Future<void> replaceDrafts(String orderId, List<MeasurementDraft> drafts);
  Future<String?> readOwnerUserId();
  Future<void> bindOwnerUserId(String userId);
  Future<bool> hasUnacknowledgedEvents();
  Future<PendingSyncBatch?> readPendingSyncBatch();
  Future<int> readSyncCursor();
  Future<void> savePendingSyncBatch(
    PendingSyncBatch batch,
    List<MeasurementDraft> drafts,
  );
  Future<void> completeSyncBatch(
    String orderId,
    List<MeasurementDraft> drafts,
    int nextSyncCursor,
  );
  Future<void> clearUserData();
}

class HiveOfflineVault implements OfflineVault {
  HiveOfflineVault({FlutterSecureStorage? secureStorage})
    : _secureStorage = secureStorage ?? const FlutterSecureStorage();

  static const _keyName = 'zenit.offline.hive-key.v1';
  static const _boxName = 'zenit_offline_v1';
  static const _ordersKey = 'prepared_orders';
  static const _ownerUserIdKey = 'owner_user_id';
  static const _pendingBatchKey = 'pending_sync_batch';
  static const _syncCursorKey = 'sync_cursor';

  final FlutterSecureStorage _secureStorage;
  Box<String>? _box;

  @override
  Future<void> initialize() async {
    await Hive.initFlutter('encrypted');
    var encodedKey = await _secureStorage.read(key: _keyName);
    if (encodedKey == null) {
      encodedKey = base64UrlEncode(Hive.generateSecureKey());
      await _secureStorage.write(key: _keyName, value: encodedKey);
    }
    final key = base64Url.decode(base64Url.normalize(encodedKey));
    if (key.length != 32) throw StateError('Invalid offline vault key');
    _box = await Hive.openBox<String>(
      _boxName,
      encryptionCipher: HiveAesCipher(key),
    );
  }

  Box<String> get _openBox =>
      _box ?? (throw StateError('Offline vault is not initialized'));

  @override
  Future<List<PreparedWorkOrder>> readOrders() async {
    final encoded = _openBox.get(_ordersKey);
    if (encoded == null) return const [];
    final items = jsonDecode(encoded) as List<Object?>;
    return items
        .map(
          (item) => PreparedWorkOrder.fromJson(
            (item! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> replaceOrders(List<PreparedWorkOrder> orders) async {
    final allowedIds = orders.map((order) => order.id).toSet();
    final pending = await readPendingSyncBatch();
    if (pending != null) allowedIds.add(pending.orderId);
    final obsoleteDraftKeys = _openBox.keys.whereType<String>().where(
      (key) =>
          key.startsWith('measurement_drafts:') &&
          !allowedIds.contains(key.substring('measurement_drafts:'.length)),
    );
    await _openBox.deleteAll(obsoleteDraftKeys);
    await _openBox.put(
      _ordersKey,
      jsonEncode(orders.map((order) => order.toJson()).toList()),
    );
  }

  @override
  Future<List<MeasurementDraft>> readDrafts(String orderId) async {
    final encoded = _openBox.get(_draftKey(orderId));
    if (encoded == null) return const [];
    final items = jsonDecode(encoded) as List<Object?>;
    return items
        .map(
          (item) =>
              MeasurementDraft.fromJson((item! as Map).cast<String, Object?>()),
        )
        .toList(growable: false);
  }

  @override
  Future<void> replaceDrafts(String orderId, List<MeasurementDraft> drafts) =>
      _openBox.put(
        _draftKey(orderId),
        jsonEncode(drafts.map((draft) => draft.toJson()).toList()),
      );

  @override
  Future<String?> readOwnerUserId() async => _openBox.get(_ownerUserIdKey);

  @override
  Future<void> bindOwnerUserId(String userId) =>
      _openBox.put(_ownerUserIdKey, userId);

  @override
  Future<bool> hasUnacknowledgedEvents() async {
    for (final key in _openBox.keys.whereType<String>()) {
      if (!key.startsWith('measurement_drafts:')) continue;
      final orderId = key.substring('measurement_drafts:'.length);
      final drafts = await readDrafts(orderId);
      if (drafts.any((draft) => !draft.hasPersistentServerResult)) return true;
    }
    return false;
  }

  @override
  Future<PendingSyncBatch?> readPendingSyncBatch() async {
    final encoded = _openBox.get(_pendingBatchKey);
    if (encoded == null) return null;
    return PendingSyncBatch.fromJson(
      (jsonDecode(encoded) as Map).cast<String, Object?>(),
    );
  }

  @override
  Future<int> readSyncCursor() async {
    final encoded = _openBox.get(_syncCursorKey);
    return encoded == null ? 0 : int.parse(encoded);
  }

  @override
  Future<void> savePendingSyncBatch(
    PendingSyncBatch batch,
    List<MeasurementDraft> drafts,
  ) => _openBox.putAll({
    _draftKey(batch.orderId): jsonEncode(
      drafts.map((draft) => draft.toJson()).toList(),
    ),
    _pendingBatchKey: jsonEncode(batch.toJson()),
  });

  @override
  Future<void> completeSyncBatch(
    String orderId,
    List<MeasurementDraft> drafts,
    int nextSyncCursor,
  ) async {
    await _openBox.putAll({
      _draftKey(orderId): jsonEncode(
        drafts.map((draft) => draft.toJson()).toList(),
      ),
      _syncCursorKey: nextSyncCursor.toString(),
    });
    await _openBox.delete(_pendingBatchKey);
  }

  @override
  Future<void> clearUserData() => _openBox.clear();

  static String _draftKey(String orderId) => 'measurement_drafts:$orderId';
}
