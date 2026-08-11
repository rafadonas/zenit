import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';

import '../domain/measurement_draft.dart';
import '../domain/demo_order_lifecycle.dart';
import '../domain/mobile_sync.dart';
import '../domain/prepared_photo_draft.dart';
import '../domain/prepared_work_order.dart';

abstract interface class OfflineVault {
  Future<void> initialize();
  Future<List<PreparedWorkOrder>> readOrders();
  Future<void> replaceOrders(List<PreparedWorkOrder> orders);
  Future<List<MeasurementDraft>> readDrafts(String orderId);
  Future<void> replaceDrafts(String orderId, List<MeasurementDraft> drafts);
  Future<List<DemoLifecycleEvent>> readLifecycleEvents(String orderId);
  Future<void> replaceLifecycleEvents(
    String orderId,
    List<DemoLifecycleEvent> events,
  );
  Future<List<PreparedPhotoDraft>> readPhotoDrafts(String orderId);
  Future<void> replacePhotoDrafts(
    String orderId,
    List<PreparedPhotoDraft> photos,
  );
  Future<String?> readOwnerUserId();
  Future<void> bindOwnerUserId(String userId);
  Future<bool> hasUnacknowledgedEvents();
  Future<PendingSyncBatch?> readPendingSyncBatch();
  Future<int> readSyncCursor();
  Future<void> savePendingSyncBatch(
    PendingSyncBatch batch,
    List<MeasurementDraft> drafts,
    List<DemoLifecycleEvent> lifecycleEvents,
    List<PreparedPhotoDraft> photoDrafts,
  );
  Future<void> completeSyncBatch(
    String orderId,
    List<MeasurementDraft> drafts,
    List<DemoLifecycleEvent> lifecycleEvents,
    List<PreparedPhotoDraft> photoDrafts,
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
    for (final key in _openBox.keys.whereType<String>()) {
      if (key.startsWith('measurement_drafts:')) {
        final orderId = key.substring('measurement_drafts:'.length);
        final drafts = await readDrafts(orderId);
        if (drafts.any((draft) => !draft.hasPersistentServerResult)) {
          allowedIds.add(orderId);
        }
      } else if (key.startsWith('demo_lifecycle:')) {
        final orderId = key.substring('demo_lifecycle:'.length);
        final events = await readLifecycleEvents(orderId);
        if (events.any((event) => !event.hasPersistentServerResult)) {
          allowedIds.add(orderId);
        }
      } else if (key.startsWith('prepared_photos:')) {
        final orderId = key.substring('prepared_photos:'.length);
        final photos = await readPhotoDrafts(orderId);
        if (photos.any((photo) => !photo.hasPersistentServerResult)) {
          allowedIds.add(orderId);
        }
      }
    }
    final obsoleteDraftKeys = _openBox.keys.whereType<String>().where(
      (key) =>
          (key.startsWith('measurement_drafts:') &&
              !allowedIds.contains(
                key.substring('measurement_drafts:'.length),
              )) ||
          (key.startsWith('demo_lifecycle:') &&
              !allowedIds.contains(key.substring('demo_lifecycle:'.length))) ||
          (key.startsWith('prepared_photos:') &&
              !allowedIds.contains(key.substring('prepared_photos:'.length))),
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
  Future<List<DemoLifecycleEvent>> readLifecycleEvents(String orderId) async {
    final encoded = _openBox.get(_lifecycleKey(orderId));
    if (encoded == null) return const [];
    final items = jsonDecode(encoded) as List<Object?>;
    return items
        .map(
          (item) => DemoLifecycleEvent.fromJson(
            (item! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> replaceLifecycleEvents(
    String orderId,
    List<DemoLifecycleEvent> events,
  ) => _openBox.put(
    _lifecycleKey(orderId),
    jsonEncode(events.map((event) => event.toJson()).toList()),
  );

  @override
  Future<List<PreparedPhotoDraft>> readPhotoDrafts(String orderId) async {
    final encoded = _openBox.get(_photoKey(orderId));
    if (encoded == null) return const [];
    final items = jsonDecode(encoded) as List<Object?>;
    return items
        .map(
          (item) => PreparedPhotoDraft.fromJson(
            (item! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> replacePhotoDrafts(
    String orderId,
    List<PreparedPhotoDraft> photos,
  ) => _openBox.put(
    _photoKey(orderId),
    jsonEncode(photos.map((photo) => photo.toJson()).toList()),
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
    for (final key in _openBox.keys.whereType<String>()) {
      if (!key.startsWith('prepared_photos:')) continue;
      final orderId = key.substring('prepared_photos:'.length);
      final photos = await readPhotoDrafts(orderId);
      if (photos.any(
        (photo) =>
            !photo.hasPersistentServerResult ||
            (photo.syncState == DraftSyncState.acknowledged &&
                !photo.isUploaded),
      )) {
        return true;
      }
    }
    for (final key in _openBox.keys.whereType<String>()) {
      if (!key.startsWith('demo_lifecycle:')) continue;
      final orderId = key.substring('demo_lifecycle:'.length);
      final events = await readLifecycleEvents(orderId);
      if (events.any((event) => !event.hasPersistentServerResult)) return true;
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
    List<DemoLifecycleEvent> lifecycleEvents,
    List<PreparedPhotoDraft> photoDrafts,
  ) => _openBox.putAll({
    _draftKey(batch.orderId): jsonEncode(
      drafts.map((draft) => draft.toJson()).toList(),
    ),
    _pendingBatchKey: jsonEncode(batch.toJson()),
    _lifecycleKey(batch.orderId): jsonEncode(
      lifecycleEvents.map((event) => event.toJson()).toList(),
    ),
    _photoKey(batch.orderId): jsonEncode(
      photoDrafts.map((photo) => photo.toJson()).toList(),
    ),
  });

  @override
  Future<void> completeSyncBatch(
    String orderId,
    List<MeasurementDraft> drafts,
    List<DemoLifecycleEvent> lifecycleEvents,
    List<PreparedPhotoDraft> photoDrafts,
    int nextSyncCursor,
  ) async {
    await _openBox.putAll({
      _draftKey(orderId): jsonEncode(
        drafts.map((draft) => draft.toJson()).toList(),
      ),
      _syncCursorKey: nextSyncCursor.toString(),
      _lifecycleKey(orderId): jsonEncode(
        lifecycleEvents.map((event) => event.toJson()).toList(),
      ),
      _photoKey(orderId): jsonEncode(
        photoDrafts.map((photo) => photo.toJson()).toList(),
      ),
    });
    await _openBox.delete(_pendingBatchKey);
  }

  @override
  Future<void> clearUserData() => _openBox.clear();

  static String _draftKey(String orderId) => 'measurement_drafts:$orderId';
  static String _lifecycleKey(String orderId) => 'demo_lifecycle:$orderId';
  static String _photoKey(String orderId) => 'prepared_photos:$orderId';
}
