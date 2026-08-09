import 'measurement_draft.dart';

class PendingSyncBatch {
  const PendingSyncBatch({
    required this.batchId,
    required this.deviceId,
    required this.orderId,
    required this.baseSyncCursor,
    required this.eventIds,
  });

  final String batchId;
  final String deviceId;
  final String orderId;
  final int baseSyncCursor;
  final List<String> eventIds;

  Map<String, Object?> toRequestJson(List<MeasurementDraft> drafts) {
    final byId = {for (final draft in drafts) draft.eventId: draft};
    if (eventIds.toSet().length != eventIds.length ||
        byId.length != drafts.length ||
        eventIds.length != drafts.length ||
        eventIds.any((eventId) => !byId.containsKey(eventId))) {
      throw StateError('Pending batch does not match the local events');
    }
    return {
      'device_id': deviceId,
      'batch_id': batchId,
      'base_sync_cursor': baseSyncCursor,
      'events': eventIds
          .map((eventId) => byId[eventId]!.toSyncEventJson())
          .toList(),
    };
  }

  Map<String, Object?> toJson() => {
    'batch_id': batchId,
    'device_id': deviceId,
    'order_id': orderId,
    'base_sync_cursor': baseSyncCursor,
    'event_ids': eventIds,
  };

  factory PendingSyncBatch.fromJson(Map<String, Object?> json) =>
      PendingSyncBatch(
        batchId: json['batch_id']! as String,
        deviceId: json['device_id']! as String,
        orderId: json['order_id']! as String,
        baseSyncCursor: json['base_sync_cursor']! as int,
        eventIds: (json['event_ids']! as List<Object?>).cast<String>(),
      );
}

class SyncEventResult {
  const SyncEventResult({required this.code, required this.message});
  final String code;
  final String message;
}

class MobileSyncResult {
  const MobileSyncResult({
    required this.batchId,
    required this.acceptedEventIds,
    required this.rejectedEvents,
    required this.conflictingEvents,
    required this.nextSyncCursor,
  });

  final String batchId;
  final Set<String> acceptedEventIds;
  final Map<String, SyncEventResult> rejectedEvents;
  final Map<String, SyncEventResult> conflictingEvents;
  final int nextSyncCursor;

  factory MobileSyncResult.fromJson(Map<String, Object?> json) {
    if (json['data_status'] != 'prepared' ||
        json['authorizes_field_work'] != false ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException('Sync response crossed a safety boundary');
    }
    final accepted = json['accepted']! as List<Object?>;
    final rejected = json['rejected']! as List<Object?>;
    final conflicts = json['conflicts']! as List<Object?>;
    final result = MobileSyncResult(
      batchId: json['batch_id']! as String,
      acceptedEventIds: accepted.map((item) {
        final value = (item! as Map).cast<String, Object?>();
        if (value['persisted'] != true) {
          throw const FormatException(
            'Accepted event lacks persistent acknowledgement',
          );
        }
        return value['event_id']! as String;
      }).toSet(),
      rejectedEvents: _eventResults(rejected),
      conflictingEvents: _eventResults(conflicts),
      nextSyncCursor: json['next_sync_cursor']! as int,
    );
    final resultCount = accepted.length + rejected.length + conflicts.length;
    final uniqueResultCount = {
      ...result.acceptedEventIds,
      ...result.rejectedEvents.keys,
      ...result.conflictingEvents.keys,
    }.length;
    if (resultCount != uniqueResultCount) {
      throw const FormatException('Sync response repeats an event result');
    }
    return result;
  }

  static Map<String, SyncEventResult> _eventResults(List<Object?> items) {
    final results = <String, SyncEventResult>{};
    for (final item in items) {
      final value = (item! as Map).cast<String, Object?>();
      results[value['event_id']! as String] = SyncEventResult(
        code: value['code']! as String,
        message: value['message']! as String,
      );
    }
    return results;
  }
}
