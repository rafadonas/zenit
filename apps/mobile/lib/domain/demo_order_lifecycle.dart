import 'measurement_draft.dart';

enum DemoLifecycleOperation { confirm, start, finish }

class DemoLifecycleEvent {
  const DemoLifecycleEvent({
    required this.eventId,
    required this.orderId,
    required this.operation,
    required this.occurredAt,
    this.simulatedLatitude,
    this.simulatedLongitude,
    this.syncState = DraftSyncState.localOnly,
    this.syncResultCode,
    this.syncResultMessage,
  });

  final String eventId;
  final String orderId;
  final DemoLifecycleOperation operation;
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

  DemoLifecycleEvent copyWith({
    DraftSyncState? syncState,
    String? syncResultCode,
    String? syncResultMessage,
    bool clearResult = false,
  }) => DemoLifecycleEvent(
    eventId: eventId,
    orderId: orderId,
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

  Map<String, Object?> toSyncEventJson() => {
    'event_id': eventId,
    'entity_type': 'work_order',
    'operation': operation.name,
    'payload': {
      'work_order_id': orderId,
      'occurred_at': occurredAt.toUtc().toIso8601String(),
      'data_status': 'simulated',
      'simulation_scope': 'demo_only',
      'authorizes_field_work': false,
      'eligible_for_official_reporting': false,
      'location_status': operation == DemoLifecycleOperation.start
          ? 'simulated'
          : 'not_collected',
      if (operation == DemoLifecycleOperation.start) ...{
        'simulated_latitude': simulatedLatitude,
        'simulated_longitude': simulatedLongitude,
        'simulation_method': 'prepared_point_demo_v1',
      },
    },
  };

  Map<String, Object?> toJson() => {
    'event_id': eventId,
    'order_id': orderId,
    'operation': operation.name,
    'occurred_at': occurredAt.toUtc().toIso8601String(),
    'simulated_latitude': simulatedLatitude,
    'simulated_longitude': simulatedLongitude,
    'sync_state': syncState.wireValue,
    'sync_result_code': syncResultCode,
    'sync_result_message': syncResultMessage,
    'data_status': 'simulated',
    'simulation_scope': 'demo_only',
    'authorizes_field_work': false,
    'eligible_for_official_reporting': false,
  };

  factory DemoLifecycleEvent.fromJson(Map<String, Object?> json) {
    if (json['data_status'] != 'simulated' ||
        json['simulation_scope'] != 'demo_only' ||
        json['authorizes_field_work'] != false ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException('Lifecycle event crossed a safety boundary');
    }
    final operation = DemoLifecycleOperation.values.byName(
      json['operation']! as String,
    );
    final latitude = (json['simulated_latitude'] as num?)?.toDouble();
    final longitude = (json['simulated_longitude'] as num?)?.toDouble();
    if ((operation == DemoLifecycleOperation.start &&
            (latitude == null ||
                longitude == null ||
                latitude < -90 ||
                latitude > 90 ||
                longitude < -180 ||
                longitude > 180)) ||
        (operation != DemoLifecycleOperation.start &&
            (latitude != null || longitude != null))) {
      throw const FormatException('Lifecycle location shape is invalid');
    }
    return DemoLifecycleEvent(
      eventId: json['event_id']! as String,
      orderId: json['order_id']! as String,
      operation: operation,
      occurredAt: DateTime.parse(json['occurred_at']! as String).toUtc(),
      simulatedLatitude: latitude,
      simulatedLongitude: longitude,
      syncState: DraftSyncState.fromWire(json['sync_state']! as String),
      syncResultCode: json['sync_result_code'] as String?,
      syncResultMessage: json['sync_result_message'] as String?,
    );
  }
}
