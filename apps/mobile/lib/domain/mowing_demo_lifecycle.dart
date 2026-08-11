import 'measurement_draft.dart';
import 'prepared_work_order.dart';

enum MowingDemoOperation { confirm, start, pause, resume, finish }

class MowingDemoLifecycleEvent {
  const MowingDemoLifecycleEvent({
    required this.eventId,
    required this.mowingOrderId,
    required this.sourcePlanningApprovalId,
    required this.operation,
    required this.occurredAt,
    this.simulatedLatitude,
    this.simulatedLongitude,
    this.syncState = DraftSyncState.localOnly,
    this.syncResultCode,
    this.syncResultMessage,
  });

  final String eventId;
  final String mowingOrderId;
  final String sourcePlanningApprovalId;
  final MowingDemoOperation operation;
  final DateTime occurredAt;
  final double? simulatedLatitude;
  final double? simulatedLongitude;
  final DraftSyncState syncState;
  final String? syncResultCode;
  final String? syncResultMessage;

  bool get hasPersistentServerResult =>
      syncState == DraftSyncState.acknowledged ||
      syncState == DraftSyncState.rejected ||
      syncState == DraftSyncState.conflict;

  MowingDemoLifecycleEvent copyWith({
    DraftSyncState? syncState,
    String? syncResultCode,
    String? syncResultMessage,
    bool clearResult = false,
  }) => MowingDemoLifecycleEvent(
    eventId: eventId,
    mowingOrderId: mowingOrderId,
    sourcePlanningApprovalId: sourcePlanningApprovalId,
    operation: operation,
    occurredAt: occurredAt,
    simulatedLatitude: simulatedLatitude,
    simulatedLongitude: simulatedLongitude,
    syncState: syncState ?? this.syncState,
    syncResultCode: clearResult ? null : syncResultCode ?? this.syncResultCode,
    syncResultMessage: clearResult
        ? null
        : syncResultMessage ?? this.syncResultMessage,
  );

  JsonMap toSyncEventJson() {
    _validateLocation();
    return {
      'event_id': eventId,
      'entity_type': 'mowing_order',
      'operation': operation.name,
      'payload': {
        'mowing_order_id': mowingOrderId,
        'source_planning_approval_id': sourcePlanningApprovalId,
        'occurred_at': occurredAt.toUtc().toIso8601String(),
        'data_status': 'simulated',
        'simulation_scope': 'demo_only',
        'rehearsal_scope': 'mowing_demo_rehearsal_only',
        'operational_approval_satisfied': false,
        'authorizes_field_work': false,
        'eligible_for_field_execution': false,
        'eligible_for_model_training': false,
        'eligible_for_official_reporting': false,
        'location_status': operation == MowingDemoOperation.start
            ? 'simulated'
            : 'not_collected',
        if (operation == MowingDemoOperation.start) ...{
          'simulated_latitude': simulatedLatitude,
          'simulated_longitude': simulatedLongitude,
          'simulation_method': 'prepared_point_demo_v1',
        },
      },
    };
  }

  JsonMap toJson() {
    _validateLocation();
    return {
      'event_id': eventId,
      'mowing_order_id': mowingOrderId,
      'source_planning_approval_id': sourcePlanningApprovalId,
      'operation': operation.name,
      'occurred_at': occurredAt.toUtc().toIso8601String(),
      'simulated_latitude': simulatedLatitude,
      'simulated_longitude': simulatedLongitude,
      'sync_state': syncState.wireValue,
      'sync_result_code': syncResultCode,
      'sync_result_message': syncResultMessage,
      'data_status': 'simulated',
      'simulation_scope': 'demo_only',
      'rehearsal_scope': 'mowing_demo_rehearsal_only',
      'operational_approval_satisfied': false,
      'authorizes_field_work': false,
      'eligible_for_field_execution': false,
      'eligible_for_model_training': false,
      'eligible_for_official_reporting': false,
    };
  }

  factory MowingDemoLifecycleEvent.fromJson(JsonMap json) {
    if (json['data_status'] != 'simulated' ||
        json['simulation_scope'] != 'demo_only' ||
        json['rehearsal_scope'] != 'mowing_demo_rehearsal_only' ||
        json['operational_approval_satisfied'] != false ||
        json['authorizes_field_work'] != false ||
        json['eligible_for_field_execution'] != false ||
        json['eligible_for_model_training'] != false ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException(
        'Mowing demo event crossed a safety boundary',
      );
    }
    final operation = MowingDemoOperation.values.byName(
      json['operation']! as String,
    );
    final latitude = (json['simulated_latitude'] as num?)?.toDouble();
    final longitude = (json['simulated_longitude'] as num?)?.toDouble();
    final hasLocation =
        latitude != null &&
        longitude != null &&
        latitude >= -90 &&
        latitude <= 90 &&
        longitude >= -180 &&
        longitude <= 180;
    if ((operation == MowingDemoOperation.start && !hasLocation) ||
        (operation != MowingDemoOperation.start &&
            (latitude != null || longitude != null))) {
      throw const FormatException('Mowing demo event has invalid location');
    }
    return MowingDemoLifecycleEvent(
      eventId: json['event_id']! as String,
      mowingOrderId: json['mowing_order_id']! as String,
      sourcePlanningApprovalId: json['source_planning_approval_id']! as String,
      operation: operation,
      occurredAt: DateTime.parse(json['occurred_at']! as String).toUtc(),
      simulatedLatitude: latitude,
      simulatedLongitude: longitude,
      syncState: DraftSyncState.fromWire(json['sync_state']! as String),
      syncResultCode: json['sync_result_code'] as String?,
      syncResultMessage: json['sync_result_message'] as String?,
    );
  }

  void _validateLocation() {
    final latitude = simulatedLatitude;
    final longitude = simulatedLongitude;
    final hasValidLocation =
        latitude != null &&
        longitude != null &&
        latitude >= -90 &&
        latitude <= 90 &&
        longitude >= -180 &&
        longitude <= 180;
    if ((operation == MowingDemoOperation.start && !hasValidLocation) ||
        (operation != MowingDemoOperation.start &&
            (latitude != null || longitude != null))) {
      throw StateError('Mowing demo event has invalid location');
    }
  }
}
