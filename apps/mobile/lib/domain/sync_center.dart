enum SyncWorkKind {
  inspectionBatch,
  inspectionPhotoUpload,
  mowingBatch,
  mowingPhotoUpload,
}

enum SyncCenterStatus { pending, sending, accepted, rejected, conflict }

class SyncAttemptRecord {
  const SyncAttemptRecord({
    required this.itemKey,
    required this.attemptCount,
    required this.lastAttemptAt,
  });

  final String itemKey;
  final int attemptCount;
  final DateTime lastAttemptAt;

  Map<String, Object?> toJson() => {
    'item_key': itemKey,
    'attempt_count': attemptCount,
    'last_attempt_at': lastAttemptAt.toUtc().toIso8601String(),
  };

  factory SyncAttemptRecord.fromJson(Map<String, Object?> json) {
    final count = json['attempt_count'];
    if (count is! int || count < 1) {
      throw const FormatException('Invalid sync attempt count');
    }
    return SyncAttemptRecord(
      itemKey: json['item_key']! as String,
      attemptCount: count,
      lastAttemptAt: DateTime.parse(json['last_attempt_at']! as String).toUtc(),
    );
  }
}

class SyncCenterItem {
  const SyncCenterItem({
    required this.key,
    required this.sourceId,
    required this.kind,
    required this.title,
    required this.subtitle,
    required this.status,
    required this.canRetry,
    required this.attemptCount,
    this.lastAttemptAt,
  });

  final String key;
  final String sourceId;
  final SyncWorkKind kind;
  final String title;
  final String subtitle;
  final SyncCenterStatus status;
  final bool canRetry;
  final int attemptCount;
  final DateTime? lastAttemptAt;
}

String syncWorkItemKey(SyncWorkKind kind, String sourceId) =>
    '${kind.name}:$sourceId';
