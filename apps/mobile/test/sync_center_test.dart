import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/domain/sync_center.dart';

void main() {
  test('sync attempt metadata round-trips for encrypted vault storage', () {
    final record = SyncAttemptRecord(
      itemKey: syncWorkItemKey(SyncWorkKind.inspectionBatch, 'order-1'),
      attemptCount: 2,
      lastAttemptAt: DateTime.utc(2026, 9, 14, 15, 30),
    );

    final restored = SyncAttemptRecord.fromJson(record.toJson());

    expect(restored.itemKey, record.itemKey);
    expect(restored.attemptCount, 2);
    expect(restored.lastAttemptAt, record.lastAttemptAt);
  });

  test('sync attempt metadata fails closed for invalid counts', () {
    expect(
      () => SyncAttemptRecord.fromJson({
        'item_key': 'inspectionBatch:order-1',
        'attempt_count': 0,
        'last_attempt_at': '2026-09-14T15:30:00Z',
      }),
      throwsFormatException,
    );
  });
}
