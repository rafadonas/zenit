enum DraftSyncState {
  localOnly('local_only'),
  pending('pending'),
  acknowledged('acknowledged'),
  rejected('rejected'),
  conflict('conflict');

  const DraftSyncState(this.wireValue);
  final String wireValue;

  static DraftSyncState fromWire(String value) => values.firstWhere(
    (state) => state.wireValue == value,
    orElse: () => throw const FormatException('Unknown draft sync state'),
  );
}

class MeasurementDraft {
  const MeasurementDraft({
    required this.eventId,
    required this.orderId,
    required this.plannedPointId,
    required this.sequence,
    required this.heightCm,
    required this.recordedAt,
    this.syncState = DraftSyncState.localOnly,
    this.syncResultCode,
    this.syncResultMessage,
  });

  final String eventId;
  final String orderId;
  final String plannedPointId;
  final int sequence;
  final double heightCm;
  final DateTime recordedAt;
  final DraftSyncState syncState;
  final String? syncResultCode;
  final String? syncResultMessage;

  String get dataStatus => 'prepared';
  bool get eligibleForOfficialReporting => false;
  bool get hasPersistentServerResult =>
      syncState == DraftSyncState.acknowledged ||
      syncState == DraftSyncState.rejected ||
      syncState == DraftSyncState.conflict;

  MeasurementDraft copyWith({
    DraftSyncState? syncState,
    String? syncResultCode,
    String? syncResultMessage,
    bool clearResult = false,
  }) => MeasurementDraft(
    eventId: eventId,
    orderId: orderId,
    plannedPointId: plannedPointId,
    sequence: sequence,
    heightCm: heightCm,
    recordedAt: recordedAt,
    syncState: syncState ?? this.syncState,
    syncResultCode: clearResult ? null : syncResultCode ?? this.syncResultCode,
    syncResultMessage: clearResult
        ? null
        : syncResultMessage ?? this.syncResultMessage,
  );

  Map<String, Object?> toSyncEventJson() => {
    'event_id': eventId,
    'entity_type': 'measurement',
    'operation': 'create',
    'payload': {
      'work_order_id': orderId,
      'planned_point_id': plannedPointId,
      'phase': 'inspection',
      'height_cm': heightCm,
      'captured_at': recordedAt.toUtc().toIso8601String(),
      'data_status': 'prepared',
      'eligible_for_official_reporting': false,
      'location_status': 'not_collected',
      'photo_status': 'not_collected',
    },
  };

  Map<String, Object?> toJson() => {
    'event_id': eventId,
    'order_id': orderId,
    'planned_point_id': plannedPointId,
    'sequence': sequence,
    'height_cm': heightCm,
    'recorded_at': recordedAt.toUtc().toIso8601String(),
    'data_status': dataStatus,
    'sync_state': syncState.wireValue,
    'sync_result_code': syncResultCode,
    'sync_result_message': syncResultMessage,
    'eligible_for_official_reporting': false,
  };

  factory MeasurementDraft.fromJson(Map<String, Object?> json) {
    if (json['data_status'] != 'prepared' ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException('Measurement is not a prepared draft');
    }
    return MeasurementDraft(
      eventId: json['event_id']! as String,
      orderId: json['order_id']! as String,
      plannedPointId: json['planned_point_id']! as String,
      sequence: json['sequence']! as int,
      heightCm: (json['height_cm']! as num).toDouble(),
      recordedAt: DateTime.parse(json['recorded_at']! as String).toUtc(),
      syncState: DraftSyncState.fromWire(json['sync_state']! as String),
      syncResultCode: json['sync_result_code'] as String?,
      syncResultMessage: json['sync_result_message'] as String?,
    );
  }
}
