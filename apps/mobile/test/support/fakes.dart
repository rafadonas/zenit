import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:zenit_mobile/data/offline_vault.dart';
import 'package:zenit_mobile/data/photo_capture.dart';
import 'package:zenit_mobile/data/device_identity_store.dart';
import 'package:zenit_mobile/data/secure_session_store.dart';
import 'package:zenit_mobile/data/zenit_gateway.dart';
import 'package:zenit_mobile/domain/auth_session.dart';
import 'package:zenit_mobile/domain/demo_order_lifecycle.dart';
import 'package:zenit_mobile/domain/measurement_draft.dart';
import 'package:zenit_mobile/domain/mobile_sync.dart';
import 'package:zenit_mobile/domain/prepared_photo_draft.dart';
import 'package:zenit_mobile/domain/prepared_work_order.dart';

Map<String, Object?> preparedOrderJson() => {
  'work_order_id': '11111111-1111-4111-8111-111111111111',
  'road_code': 'SP-001',
  'segment_index': 12,
  'zone_type': 'left',
  'planning_rationale': 'Prepared inspection only',
  'created_at': '2026-08-09T12:00:00Z',
  'status': 'prepared',
  'order_type': 'inspection',
  'order_data_status': 'prepared',
  'authorizes_field_work': false,
  'eligible_for_field_execution': false,
  'eligible_for_official_reporting': false,
  'planned_points': List.generate(
    3,
    (index) => {
      'planned_point_id': '22222222-2222-4222-8222-22222222222${index + 1}',
      'sequence': index + 1,
      'position_fraction': [1 / 6, 1 / 2, 5 / 6][index],
      'longitude': -46.6 + index / 100,
      'latitude': -23.5 + index / 100,
      'geometry_srid': 4326,
      'planning_method': 'segment_centerline_fraction',
      'data_status': 'estimated',
      'eligible_for_field_execution': false,
    },
  ),
};

PreparedWorkOrder preparedOrder() =>
    PreparedWorkOrder.fromJson(preparedOrderJson());

AuthSession validSession() => AuthSession(
  accessToken: 'token',
  expiresAt: DateTime.utc(2030),
  userId: '33333333-3333-4333-8333-333333333333',
  email: 'field@example.test',
  displayName: 'Field User',
);

class FakeGateway implements ZenitGateway {
  FakeGateway({
    this.orders = const [],
    this.syncFailure,
    this.loginSession,
    this.syncResultFactory,
  });
  List<PreparedWorkOrder> orders;
  Object? syncFailure;
  AuthSession? loginSession;
  MobileSyncResult Function(PendingSyncBatch batch)? syncResultFactory;
  int registrationCalls = 0;
  int syncCalls = 0;
  PendingSyncBatch? lastBatch;
  List<Map<String, Object?>>? lastEvents;

  @override
  Future<AuthSession> login(String email, String password) async =>
      loginSession ?? validSession();

  @override
  Future<List<PreparedWorkOrder>> listPreparedOrders(
    String accessToken,
  ) async => orders;

  @override
  Future<void> registerDevice(
    String accessToken,
    String deviceId,
    String appVersion,
  ) async {
    registrationCalls++;
  }

  @override
  Future<MobileSyncResult> syncBatch(
    String accessToken,
    PendingSyncBatch batch,
    List<Map<String, Object?>> events,
  ) async {
    syncCalls++;
    lastBatch = batch;
    lastEvents = events;
    if (syncFailure case final failure?) throw failure;
    if (syncResultFactory case final factory?) return factory(batch);
    return MobileSyncResult(
      batchId: batch.batchId,
      acceptedEventIds: batch.eventIds.toSet(),
      rejectedEvents: const {},
      conflictingEvents: const {},
      nextSyncCursor: batch.baseSyncCursor + 1,
    );
  }
}

class MemoryDeviceIdentityStore implements DeviceIdentityStore {
  String? value = '44444444-4444-4444-8444-444444444444';

  @override
  Future<void> clear() async => value = null;

  @override
  Future<String> readOrCreate() async =>
      value ??= '44444444-4444-4444-8444-444444444444';
}

class FakePhotoCapture implements PhotoCapture {
  @override
  Future<CapturedPhoto?> capture() async {
    final bytes = Uint8List.fromList([0xff, 0xd8, 0xff, 0xd9]);
    return CapturedPhoto(
      bytes: bytes,
      mediaType: 'image/jpeg',
      checksumSha256: sha256.convert(bytes).toString(),
    );
  }
}

class MemorySessionStore implements SessionStore {
  AuthSession? value;

  @override
  Future<void> clear() async => value = null;

  @override
  Future<AuthSession?> readValid(DateTime now) async =>
      value?.isValidAt(now) == true ? value : null;

  @override
  Future<void> write(AuthSession session) async => value = session;
}

class MemoryVault implements OfflineVault {
  List<PreparedWorkOrder> orders = const [];
  final Map<String, List<MeasurementDraft>> drafts = {};
  final Map<String, List<DemoLifecycleEvent>> lifecycleEvents = {};
  final Map<String, List<PreparedPhotoDraft>> photoDrafts = {};
  String? ownerUserId;
  PendingSyncBatch? pendingBatch;
  int syncCursor = 0;

  @override
  Future<void> initialize() async {}

  @override
  Future<void> clearUserData() async {
    orders = const [];
    drafts.clear();
    lifecycleEvents.clear();
    photoDrafts.clear();
    ownerUserId = null;
    pendingBatch = null;
    syncCursor = 0;
  }

  @override
  Future<List<MeasurementDraft>> readDrafts(String orderId) async =>
      drafts[orderId] ?? const [];

  @override
  Future<List<PreparedWorkOrder>> readOrders() async => orders;

  @override
  Future<List<DemoLifecycleEvent>> readLifecycleEvents(String orderId) async =>
      lifecycleEvents[orderId] ?? const [];

  @override
  Future<List<PreparedPhotoDraft>> readPhotoDrafts(String orderId) async =>
      photoDrafts[orderId] ?? const [];

  @override
  Future<void> replaceDrafts(
    String orderId,
    List<MeasurementDraft> values,
  ) async => drafts[orderId] = List.unmodifiable(values);

  @override
  Future<void> replaceOrders(List<PreparedWorkOrder> values) async =>
      orders = List.unmodifiable(values);

  @override
  Future<void> replaceLifecycleEvents(
    String orderId,
    List<DemoLifecycleEvent> values,
  ) async => lifecycleEvents[orderId] = List.unmodifiable(values);

  @override
  Future<void> replacePhotoDrafts(
    String orderId,
    List<PreparedPhotoDraft> values,
  ) async => photoDrafts[orderId] = List.unmodifiable(values);

  @override
  Future<void> bindOwnerUserId(String userId) async => ownerUserId = userId;

  @override
  Future<void> completeSyncBatch(
    String orderId,
    List<MeasurementDraft> values,
    List<DemoLifecycleEvent> lifecycleValues,
    List<PreparedPhotoDraft> photoValues,
    int nextSyncCursor,
  ) async {
    drafts[orderId] = List.unmodifiable(values);
    lifecycleEvents[orderId] = List.unmodifiable(lifecycleValues);
    photoDrafts[orderId] = List.unmodifiable(photoValues);
    syncCursor = nextSyncCursor;
    pendingBatch = null;
  }

  @override
  Future<bool> hasUnacknowledgedEvents() async =>
      drafts.values
          .expand((values) => values)
          .any((draft) => !draft.hasPersistentServerResult) ||
      lifecycleEvents.values
          .expand((values) => values)
          .any((event) => !event.hasPersistentServerResult) ||
      photoDrafts.values
          .expand((values) => values)
          .any((photo) => !photo.hasPersistentServerResult);

  @override
  Future<String?> readOwnerUserId() async => ownerUserId;

  @override
  Future<PendingSyncBatch?> readPendingSyncBatch() async => pendingBatch;

  @override
  Future<int> readSyncCursor() async => syncCursor;

  @override
  Future<void> savePendingSyncBatch(
    PendingSyncBatch batch,
    List<MeasurementDraft> values,
    List<DemoLifecycleEvent> lifecycleValues,
    List<PreparedPhotoDraft> photoValues,
  ) async {
    pendingBatch = batch;
    drafts[batch.orderId] = List.unmodifiable(values);
    lifecycleEvents[batch.orderId] = List.unmodifiable(lifecycleValues);
    photoDrafts[batch.orderId] = List.unmodifiable(photoValues);
  }
}
