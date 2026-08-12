import 'measurement_draft.dart';
import 'prepared_work_order.dart';

class MowingPostServiceMeasurementDraft {
  const MowingPostServiceMeasurementDraft({
    required this.eventId,
    required this.mowingOrderId,
    required this.sourcePlanningApprovalId,
    required this.sourcePlannedPointId,
    required this.sequence,
    required this.heightCm,
    required this.capturedAt,
    this.syncState = DraftSyncState.localOnly,
    this.syncResultCode,
    this.syncResultMessage,
  });

  final String eventId;
  final String mowingOrderId;
  final String sourcePlanningApprovalId;
  final String sourcePlannedPointId;
  final int sequence;
  final double heightCm;
  final DateTime capturedAt;
  final DraftSyncState syncState;
  final String? syncResultCode;
  final String? syncResultMessage;

  bool get hasPersistentServerResult =>
      syncState == DraftSyncState.acknowledged ||
      syncState == DraftSyncState.rejected ||
      syncState == DraftSyncState.conflict;

  MowingPostServiceMeasurementDraft copyWith({
    DraftSyncState? syncState,
    String? syncResultCode,
    String? syncResultMessage,
    bool clearResult = false,
  }) => MowingPostServiceMeasurementDraft(
    eventId: eventId,
    mowingOrderId: mowingOrderId,
    sourcePlanningApprovalId: sourcePlanningApprovalId,
    sourcePlannedPointId: sourcePlannedPointId,
    sequence: sequence,
    heightCm: heightCm,
    capturedAt: capturedAt,
    syncState: syncState ?? this.syncState,
    syncResultCode: clearResult ? null : syncResultCode ?? this.syncResultCode,
    syncResultMessage: clearResult
        ? null
        : syncResultMessage ?? this.syncResultMessage,
  );

  JsonMap toSyncEventJson() {
    _validateValues();
    return {
      'event_id': eventId,
      'entity_type': 'mowing_measurement',
      'operation': 'create',
      'payload': {
        'mowing_order_id': mowingOrderId,
        'source_planning_approval_id': sourcePlanningApprovalId,
        'source_planned_point_id': sourcePlannedPointId,
        'phase': 'post_service',
        'height_cm': heightCm,
        'captured_at': capturedAt.toUtc().toIso8601String(),
        'measurement_scope': 'mowing_demo_post_service_only',
        'location_status': 'not_collected',
        'photo_status': 'not_collected',
        'data_status': 'simulated',
        'quality_status': 'simulated_unverified',
        'operational_approval_satisfied': false,
        'authorizes_field_work': false,
        'eligible_for_field_execution': false,
        'eligible_for_model_training': false,
        'eligible_for_official_reporting': false,
      },
    };
  }

  JsonMap toJson() {
    _validateValues();
    return {
      'event_id': eventId,
      'mowing_order_id': mowingOrderId,
      'source_planning_approval_id': sourcePlanningApprovalId,
      'source_planned_point_id': sourcePlannedPointId,
      'sequence': sequence,
      'height_cm': heightCm,
      'captured_at': capturedAt.toUtc().toIso8601String(),
      'phase': 'post_service',
      'measurement_scope': 'mowing_demo_post_service_only',
      'location_status': 'not_collected',
      'photo_status': 'not_collected',
      'data_status': 'simulated',
      'quality_status': 'simulated_unverified',
      'operational_approval_satisfied': false,
      'authorizes_field_work': false,
      'eligible_for_field_execution': false,
      'eligible_for_model_training': false,
      'eligible_for_official_reporting': false,
      'sync_state': syncState.wireValue,
      'sync_result_code': syncResultCode,
      'sync_result_message': syncResultMessage,
    };
  }

  factory MowingPostServiceMeasurementDraft.fromJson(JsonMap json) {
    if (json['phase'] != 'post_service' ||
        json['measurement_scope'] != 'mowing_demo_post_service_only' ||
        json['location_status'] != 'not_collected' ||
        json['photo_status'] != 'not_collected' ||
        json['data_status'] != 'simulated' ||
        json['quality_status'] != 'simulated_unverified' ||
        json['operational_approval_satisfied'] != false ||
        json['authorizes_field_work'] != false ||
        json['eligible_for_field_execution'] != false ||
        json['eligible_for_model_training'] != false ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException(
        'Mowing post-service measurement crossed a safety boundary',
      );
    }
    final draft = MowingPostServiceMeasurementDraft(
      eventId: json['event_id']! as String,
      mowingOrderId: json['mowing_order_id']! as String,
      sourcePlanningApprovalId: json['source_planning_approval_id']! as String,
      sourcePlannedPointId: json['source_planned_point_id']! as String,
      sequence: json['sequence']! as int,
      heightCm: (json['height_cm']! as num).toDouble(),
      capturedAt: DateTime.parse(json['captured_at']! as String).toUtc(),
      syncState: DraftSyncState.fromWire(json['sync_state']! as String),
      syncResultCode: json['sync_result_code'] as String?,
      syncResultMessage: json['sync_result_message'] as String?,
    );
    try {
      draft._validateValues();
    } on StateError catch (error) {
      throw FormatException(error.message);
    }
    return draft;
  }

  void _validateValues() {
    if (eventId.isEmpty ||
        mowingOrderId.isEmpty ||
        sourcePlanningApprovalId.isEmpty ||
        sourcePlannedPointId.isEmpty ||
        sequence < 1 ||
        sequence > 3 ||
        !heightCm.isFinite ||
        heightCm < 0 ||
        heightCm > 1000) {
      throw StateError('Mowing post-service measurement is invalid');
    }
  }
}
