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
import 'package:zenit_mobile/domain/mowing_demo_lifecycle.dart';
import 'package:zenit_mobile/domain/mowing_post_service_measurement_draft.dart';
import 'package:zenit_mobile/domain/prepared_mowing_plan.dart';
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
  'eligible_for_model_training': false,
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

Map<String, Object?> preparedMowingPlanJson() => {
  'mowing_order_id': '90000000-0000-4000-8000-000000000001',
  'proposal_id': '90000000-0000-4000-8000-000000000002',
  'source_review_id': '90000000-0000-4000-8000-000000000003',
  'source_inspection_work_order_id': '11111111-1111-4111-8111-111111111111',
  'road_code': 'SP-001',
  'segment_index': 12,
  'zone_type': 'left',
  'creation_recommendation': 'mowing_review',
  'source_review_state': 'effective',
  'order_type': 'mowing',
  'status': 'prepared',
  'version': 1,
  'planning_rationale': 'Prepared planning demonstration only',
  'creation_policy_version': 'prepared-mowing-order-v1',
  'data_status': 'prepared',
  'location_status': 'simulated',
  'source_evidence_status': 'prepared_reviewed_non_operational',
  'team_assignment_status': 'unassigned',
  'equipment_assignment_status': 'unassigned',
  'weather_check_status': 'pending',
  'safety_check_status': 'pending',
  'requires_operational_approval': true,
  'authorizes_field_work': false,
  'eligible_for_field_execution': false,
  'eligible_for_model_training': false,
  'eligible_for_official_reporting': false,
  'created_at': '2026-08-11T12:00:00Z',
  'resource_plan_count': 1,
  'latest_resource_plan_id': '90000000-0000-4000-8000-000000000004',
  'latest_team_reference': 'TEAM-CANDIDATE-01',
  'latest_equipment_reference': 'EQUIPMENT-CANDIDATE-01',
  'latest_resource_plan_rationale': 'Candidate resources for validation',
  'latest_resource_plan_created_at': '2026-08-11T12:10:00Z',
  'resource_plan_state': 'candidate_resources_pending_validation',
  'readiness_assessment_count': 1,
  'latest_readiness_assessment_id': '90000000-0000-4000-8000-000000000005',
  'latest_readiness_resource_plan_id': '90000000-0000-4000-8000-000000000004',
  'latest_weather_result': 'clear',
  'latest_weather_source_reference': 'MANUAL-WEATHER-01',
  'latest_safety_result': 'clear',
  'latest_safety_source_reference': 'MANUAL-SAFETY-01',
  'latest_readiness_rationale': 'Manual prepared assessment',
  'latest_readiness_assessed_at': '2026-08-11T12:20:00Z',
  'planning_approval_count': 1,
  'latest_planning_approval_id': '90000000-0000-4000-8000-000000000006',
  'latest_planning_approval_readiness_id':
      '90000000-0000-4000-8000-000000000005',
  'latest_planning_decision': 'approved_for_planning',
  'latest_planning_decision_rationale': 'Planning review only',
  'latest_planning_decided_at': '2026-08-11T12:30:00Z',
  'operational_approval_satisfied': false,
};

PreparedMowingPlan preparedMowingPlan() =>
    PreparedMowingPlan.fromJson(preparedMowingPlanJson());

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
    this.mowingPlans = const [],
    this.syncFailure,
    this.loginSession,
    this.syncResultFactory,
  });
  List<PreparedWorkOrder> orders;
  List<PreparedMowingPlan> mowingPlans;
  Object? syncFailure;
  AuthSession? loginSession;
  MobileSyncResult Function(PendingSyncBatch batch)? syncResultFactory;
  int registrationCalls = 0;
  int syncCalls = 0;
  Object? uploadFailure;
  int? uploadFailureAtCall;
  int uploadCalls = 0;
  final List<String> uploadedPhotoIds = [];
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
  Future<List<PreparedMowingPlan>> listPreparedMowingPlans(
    String accessToken,
  ) async => mowingPlans;

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

  @override
  Future<void> uploadPreparedPhoto(
    String accessToken,
    String deviceId,
    PreparedPhotoDraft photo,
  ) async {
    uploadCalls++;
    if (uploadFailure case final failure?
        when uploadFailureAtCall == null ||
            uploadFailureAtCall == uploadCalls) {
      throw failure;
    }
    uploadedPhotoIds.add(photo.photoId);
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
  List<PreparedMowingPlan> mowingPlans = const [];
  final Map<String, List<MeasurementDraft>> drafts = {};
  final Map<String, List<DemoLifecycleEvent>> lifecycleEvents = {};
  final Map<String, List<MowingDemoLifecycleEvent>> mowingLifecycleEvents = {};
  final Map<String, List<MowingPostServiceMeasurementDraft>>
  mowingPostServiceMeasurements = {};
  final Map<String, List<PreparedPhotoDraft>> photoDrafts = {};
  String? ownerUserId;
  PendingSyncBatch? pendingBatch;
  int syncCursor = 0;

  @override
  Future<void> initialize() async {}

  @override
  Future<void> clearUserData() async {
    orders = const [];
    mowingPlans = const [];
    drafts.clear();
    lifecycleEvents.clear();
    mowingLifecycleEvents.clear();
    mowingPostServiceMeasurements.clear();
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
  Future<List<PreparedMowingPlan>> readMowingPlans() async => mowingPlans;

  @override
  Future<List<DemoLifecycleEvent>> readLifecycleEvents(String orderId) async =>
      lifecycleEvents[orderId] ?? const [];

  @override
  Future<List<MowingDemoLifecycleEvent>> readMowingLifecycleEvents(
    String mowingOrderId,
  ) async => mowingLifecycleEvents[mowingOrderId] ?? const [];

  @override
  Future<List<MowingPostServiceMeasurementDraft>>
  readMowingPostServiceMeasurements(String mowingOrderId) async =>
      mowingPostServiceMeasurements[mowingOrderId] ?? const [];

  @override
  Future<List<PreparedPhotoDraft>> readPhotoDrafts(String orderId) async =>
      photoDrafts[orderId] ?? const [];

  @override
  Future<void> replaceDrafts(
    String orderId,
    List<MeasurementDraft> values,
  ) async => drafts[orderId] = List.unmodifiable(values);

  @override
  Future<void> replaceOrders(List<PreparedWorkOrder> values) async {
    final retainedIds = <String>{};
    for (final plan in mowingPlans) {
      final lifecycle = mowingLifecycleEvents[plan.id] ?? const [];
      final measurements = mowingPostServiceMeasurements[plan.id] ?? const [];
      if (pendingBatch?.orderId == plan.id ||
          lifecycle.any((event) => !event.hasPersistentServerResult) ||
          measurements.any((item) => !item.hasPersistentServerResult)) {
        retainedIds.add(plan.sourceInspectionWorkOrderId);
      }
    }
    final merged = <String, PreparedWorkOrder>{
      for (final order in orders)
        if (retainedIds.contains(order.id)) order.id: order,
      for (final order in values) order.id: order,
    };
    orders = List.unmodifiable(merged.values);
  }

  @override
  Future<void> replaceMowingPlans(List<PreparedMowingPlan> values) async =>
      mowingPlans = List.unmodifiable(values);

  @override
  Future<void> replaceMowingLifecycleEvents(
    String mowingOrderId,
    List<MowingDemoLifecycleEvent> values,
  ) async => mowingLifecycleEvents[mowingOrderId] = List.unmodifiable(values);

  @override
  Future<void> replaceMowingPostServiceMeasurements(
    String mowingOrderId,
    List<MowingPostServiceMeasurementDraft> values,
  ) async =>
      mowingPostServiceMeasurements[mowingOrderId] = List.unmodifiable(values);

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
      mowingLifecycleEvents.values
          .expand((values) => values)
          .any((event) => !event.hasPersistentServerResult) ||
      mowingPostServiceMeasurements.values
          .expand((values) => values)
          .any((item) => !item.hasPersistentServerResult) ||
      photoDrafts.values
          .expand((values) => values)
          .any(
            (photo) =>
                !photo.hasPersistentServerResult ||
                (photo.syncState == DraftSyncState.acknowledged &&
                    !photo.isUploaded),
          );

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

  @override
  Future<void> savePendingMowingSyncBatch(
    PendingSyncBatch batch,
    List<MowingDemoLifecycleEvent> lifecycleValues,
    List<MowingPostServiceMeasurementDraft> measurementValues,
  ) async {
    pendingBatch = batch;
    mowingLifecycleEvents[batch.orderId] = List.unmodifiable(lifecycleValues);
    mowingPostServiceMeasurements[batch.orderId] = List.unmodifiable(
      measurementValues,
    );
  }

  @override
  Future<void> completeMowingSyncBatch(
    String mowingOrderId,
    List<MowingDemoLifecycleEvent> lifecycleValues,
    List<MowingPostServiceMeasurementDraft> measurementValues,
    int nextSyncCursor,
  ) async {
    mowingLifecycleEvents[mowingOrderId] = List.unmodifiable(lifecycleValues);
    mowingPostServiceMeasurements[mowingOrderId] = List.unmodifiable(
      measurementValues,
    );
    syncCursor = nextSyncCursor;
    pendingBatch = null;
  }
}
