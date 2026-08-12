import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';

import '../domain/measurement_draft.dart';
import '../domain/demo_order_lifecycle.dart';
import '../domain/mobile_sync.dart';
import '../domain/mowing_demo_lifecycle.dart';
import '../domain/mowing_post_service_measurement_draft.dart';
import '../domain/prepared_mowing_plan.dart';
import '../domain/prepared_photo_draft.dart';
import '../domain/prepared_work_order.dart';

abstract interface class OfflineVault {
  Future<void> initialize();
  Future<List<PreparedWorkOrder>> readOrders();
  Future<void> replaceOrders(List<PreparedWorkOrder> orders);
  Future<List<PreparedMowingPlan>> readMowingPlans();
  Future<void> replaceMowingPlans(List<PreparedMowingPlan> plans);
  Future<List<MowingDemoLifecycleEvent>> readMowingLifecycleEvents(
    String mowingOrderId,
  );
  Future<void> replaceMowingLifecycleEvents(
    String mowingOrderId,
    List<MowingDemoLifecycleEvent> events,
  );
  Future<List<MowingPostServiceMeasurementDraft>>
  readMowingPostServiceMeasurements(String mowingOrderId);
  Future<void> replaceMowingPostServiceMeasurements(
    String mowingOrderId,
    List<MowingPostServiceMeasurementDraft> measurements,
  );
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
  Future<void> savePendingMowingSyncBatch(
    PendingSyncBatch batch,
    List<MowingDemoLifecycleEvent> lifecycleEvents,
    List<MowingPostServiceMeasurementDraft> measurements,
  );
  Future<void> completeMowingSyncBatch(
    String mowingOrderId,
    List<MowingDemoLifecycleEvent> lifecycleEvents,
    List<MowingPostServiceMeasurementDraft> measurements,
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
  static const _mowingPlansKey = 'prepared_mowing_plans';
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
    final existingMowingPlans = await readMowingPlans();
    for (final plan in existingMowingPlans) {
      final lifecycle = await readMowingLifecycleEvents(plan.id);
      final measurements = await readMowingPostServiceMeasurements(plan.id);
      final hasUnacknowledgedMowingData =
          lifecycle.any((event) => !event.hasPersistentServerResult) ||
          measurements.any((item) => !item.hasPersistentServerResult);
      if (pending?.orderId == plan.id || hasUnacknowledgedMowingData) {
        allowedIds.add(plan.sourceInspectionWorkOrderId);
      }
    }
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
    final existing = await readOrders();
    final merged = <String, PreparedWorkOrder>{
      for (final order in existing)
        if (allowedIds.contains(order.id)) order.id: order,
      for (final order in orders) order.id: order,
    };
    final retainedOrderIds = merged.keys.toSet();
    final obsoleteDraftKeys = _openBox.keys.whereType<String>().where(
      (key) =>
          (key.startsWith('measurement_drafts:') &&
              !retainedOrderIds.contains(
                key.substring('measurement_drafts:'.length),
              )) ||
          (key.startsWith('demo_lifecycle:') &&
              !retainedOrderIds.contains(
                key.substring('demo_lifecycle:'.length),
              )) ||
          (key.startsWith('prepared_photos:') &&
              !retainedOrderIds.contains(
                key.substring('prepared_photos:'.length),
              )),
    );
    await _openBox.deleteAll(obsoleteDraftKeys);
    await _openBox.put(
      _ordersKey,
      jsonEncode(merged.values.map((order) => order.toJson()).toList()),
    );
  }

  @override
  Future<List<PreparedMowingPlan>> readMowingPlans() async {
    final encoded = _openBox.get(_mowingPlansKey);
    if (encoded == null) return const [];
    final items = jsonDecode(encoded) as List<Object?>;
    return items
        .map(
          (item) => PreparedMowingPlan.fromJson(
            (item! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> replaceMowingPlans(List<PreparedMowingPlan> plans) async {
    final retainedIds = <String>{};
    final pending = await readPendingSyncBatch();
    if (pending != null) retainedIds.add(pending.orderId);
    for (final key in _openBox.keys.whereType<String>()) {
      if (!key.startsWith('mowing_demo_lifecycle:')) continue;
      final orderId = key.substring('mowing_demo_lifecycle:'.length);
      final events = await readMowingLifecycleEvents(orderId);
      if (events.any((event) => !event.hasPersistentServerResult)) {
        retainedIds.add(orderId);
      }
    }
    for (final key in _openBox.keys.whereType<String>()) {
      if (!key.startsWith('mowing_post_service_measurements:')) continue;
      final orderId = key.substring('mowing_post_service_measurements:'.length);
      final measurements = await readMowingPostServiceMeasurements(orderId);
      if (measurements.any((item) => !item.hasPersistentServerResult)) {
        retainedIds.add(orderId);
      }
    }
    final existing = await readMowingPlans();
    final merged = <String, PreparedMowingPlan>{
      for (final plan in existing)
        if (retainedIds.contains(plan.id)) plan.id: plan,
      for (final plan in plans) plan.id: plan,
    };
    final allowedIds = merged.keys.toSet();
    final obsoleteKeys = _openBox.keys.whereType<String>().where(
      (key) =>
          (key.startsWith('mowing_demo_lifecycle:') &&
              !allowedIds.contains(
                key.substring('mowing_demo_lifecycle:'.length),
              )) ||
          (key.startsWith('mowing_post_service_measurements:') &&
              !allowedIds.contains(
                key.substring('mowing_post_service_measurements:'.length),
              )),
    );
    await _openBox.deleteAll(obsoleteKeys);
    await _openBox.put(
      _mowingPlansKey,
      jsonEncode(merged.values.map((plan) => plan.toJson()).toList()),
    );
  }

  @override
  Future<List<MowingDemoLifecycleEvent>> readMowingLifecycleEvents(
    String mowingOrderId,
  ) async {
    final encoded = _openBox.get(_mowingLifecycleKey(mowingOrderId));
    if (encoded == null) return const [];
    final items = jsonDecode(encoded) as List<Object?>;
    return items
        .map(
          (item) => MowingDemoLifecycleEvent.fromJson(
            (item! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> replaceMowingLifecycleEvents(
    String mowingOrderId,
    List<MowingDemoLifecycleEvent> events,
  ) => _openBox.put(
    _mowingLifecycleKey(mowingOrderId),
    jsonEncode(events.map((event) => event.toJson()).toList()),
  );

  @override
  Future<List<MowingPostServiceMeasurementDraft>>
  readMowingPostServiceMeasurements(String mowingOrderId) async {
    final encoded = _openBox.get(_mowingMeasurementKey(mowingOrderId));
    if (encoded == null) return const [];
    final items = jsonDecode(encoded) as List<Object?>;
    return items
        .map(
          (item) => MowingPostServiceMeasurementDraft.fromJson(
            (item! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> replaceMowingPostServiceMeasurements(
    String mowingOrderId,
    List<MowingPostServiceMeasurementDraft> measurements,
  ) => _openBox.put(
    _mowingMeasurementKey(mowingOrderId),
    jsonEncode(measurements.map((item) => item.toJson()).toList()),
  );

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
    for (final key in _openBox.keys.whereType<String>()) {
      if (!key.startsWith('mowing_demo_lifecycle:')) continue;
      final orderId = key.substring('mowing_demo_lifecycle:'.length);
      final events = await readMowingLifecycleEvents(orderId);
      if (events.any((event) => !event.hasPersistentServerResult)) return true;
    }
    for (final key in _openBox.keys.whereType<String>()) {
      if (!key.startsWith('mowing_post_service_measurements:')) continue;
      final orderId = key.substring('mowing_post_service_measurements:'.length);
      final measurements = await readMowingPostServiceMeasurements(orderId);
      if (measurements.any((item) => !item.hasPersistentServerResult)) {
        return true;
      }
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
  Future<void> savePendingMowingSyncBatch(
    PendingSyncBatch batch,
    List<MowingDemoLifecycleEvent> lifecycleEvents,
    List<MowingPostServiceMeasurementDraft> measurements,
  ) => _openBox.putAll({
    _mowingLifecycleKey(batch.orderId): jsonEncode(
      lifecycleEvents.map((event) => event.toJson()).toList(),
    ),
    _mowingMeasurementKey(batch.orderId): jsonEncode(
      measurements.map((item) => item.toJson()).toList(),
    ),
    _pendingBatchKey: jsonEncode(batch.toJson()),
  });

  @override
  Future<void> completeMowingSyncBatch(
    String mowingOrderId,
    List<MowingDemoLifecycleEvent> lifecycleEvents,
    List<MowingPostServiceMeasurementDraft> measurements,
    int nextSyncCursor,
  ) async {
    await _openBox.putAll({
      _mowingLifecycleKey(mowingOrderId): jsonEncode(
        lifecycleEvents.map((event) => event.toJson()).toList(),
      ),
      _mowingMeasurementKey(mowingOrderId): jsonEncode(
        measurements.map((item) => item.toJson()).toList(),
      ),
      _syncCursorKey: nextSyncCursor.toString(),
    });
    await _openBox.delete(_pendingBatchKey);
  }

  @override
  Future<void> clearUserData() => _openBox.clear();

  static String _draftKey(String orderId) => 'measurement_drafts:$orderId';
  static String _lifecycleKey(String orderId) => 'demo_lifecycle:$orderId';
  static String _photoKey(String orderId) => 'prepared_photos:$orderId';
  static String _mowingLifecycleKey(String orderId) =>
      'mowing_demo_lifecycle:$orderId';
  static String _mowingMeasurementKey(String orderId) =>
      'mowing_post_service_measurements:$orderId';
}
