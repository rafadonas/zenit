import 'dart:math';

import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/data/device_identity_store.dart';
import 'package:zenit_mobile/domain/measurement_draft.dart';
import 'package:zenit_mobile/domain/mobile_sync.dart';

void main() {
  test('generated UUID has version 4 and RFC 4122 variant bits', () {
    final value = generateUuidV4(Random(123));

    expect(
      value,
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
  });

  test('sync response rejects any operational or non-persistent claim', () {
    final payload = {
      'batch_id': '55555555-5555-4555-8555-555555555555',
      'accepted': [
        {
          'event_id': '66666666-6666-4666-8666-666666666666',
          'persisted': false,
        },
      ],
      'rejected': [],
      'conflicts': [],
      'next_sync_cursor': 1,
      'data_status': 'prepared',
      'authorizes_field_work': false,
      'eligible_for_official_reporting': false,
    };

    expect(() => MobileSyncResult.fromJson(payload), throwsFormatException);
    payload['accepted'] = [];
    payload['authorizes_field_work'] = true;
    expect(() => MobileSyncResult.fromJson(payload), throwsFormatException);
  });

  test('sync response cannot classify one event twice', () {
    final payload = {
      'batch_id': '55555555-5555-4555-8555-555555555555',
      'accepted': [
        {'event_id': '66666666-6666-4666-8666-666666666666', 'persisted': true},
      ],
      'rejected': [
        {
          'event_id': '66666666-6666-4666-8666-666666666666',
          'code': 'duplicate',
          'message': 'duplicate result',
        },
      ],
      'conflicts': [],
      'next_sync_cursor': 1,
      'data_status': 'prepared',
      'authorizes_field_work': false,
      'eligible_for_official_reporting': false,
    };

    expect(() => MobileSyncResult.fromJson(payload), throwsFormatException);
  });

  test('pending event and batch identifiers survive local serialization', () {
    final draft = MeasurementDraft(
      eventId: '66666666-6666-4666-8666-666666666666',
      orderId: '11111111-1111-4111-8111-111111111111',
      plannedPointId: '22222222-2222-4222-8222-222222222221',
      sequence: 1,
      heightCm: 22.5,
      recordedAt: DateTime.utc(2026, 8, 9, 17),
      syncState: DraftSyncState.pending,
    );
    const batch = PendingSyncBatch(
      batchId: '55555555-5555-4555-8555-555555555555',
      deviceId: '44444444-4444-4444-8444-444444444444',
      orderId: '11111111-1111-4111-8111-111111111111',
      baseSyncCursor: 3,
      eventIds: ['66666666-6666-4666-8666-666666666666'],
    );

    final restoredDraft = MeasurementDraft.fromJson(draft.toJson());
    final restoredBatch = PendingSyncBatch.fromJson(batch.toJson());

    expect(restoredDraft.eventId, draft.eventId);
    expect(restoredDraft.syncState, DraftSyncState.pending);
    expect(restoredBatch.batchId, batch.batchId);
    expect(restoredBatch.eventIds, batch.eventIds);
  });

  test('pending batch must match every local event exactly once', () {
    final draft = MeasurementDraft(
      eventId: '66666666-6666-4666-8666-666666666666',
      orderId: '11111111-1111-4111-8111-111111111111',
      plannedPointId: '22222222-2222-4222-8222-222222222221',
      sequence: 1,
      heightCm: 22.5,
      recordedAt: DateTime.utc(2026, 8, 9, 17),
      syncState: DraftSyncState.pending,
    );
    const batch = PendingSyncBatch(
      batchId: '55555555-5555-4555-8555-555555555555',
      deviceId: '44444444-4444-4444-8444-444444444444',
      orderId: '11111111-1111-4111-8111-111111111111',
      baseSyncCursor: 3,
      eventIds: [
        '66666666-6666-4666-8666-666666666666',
        '66666666-6666-4666-8666-666666666666',
      ],
    );

    expect(() => batch.toRequestJson([draft]), throwsStateError);
  });
}
