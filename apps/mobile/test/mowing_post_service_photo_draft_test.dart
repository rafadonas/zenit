import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/domain/mowing_post_service_photo_draft.dart';

void main() {
  test('round-trips encrypted bytes and emits only a safe manifest', () {
    final draft = _draft();

    final restored = MowingPostServicePhotoDraft.fromJson(draft.toJson());
    final event = draft.toSyncEventJson();
    final payload = (event['payload']! as Map).cast<String, Object?>();

    expect(restored.bytes, draft.bytes);
    expect(event['entity_type'], 'mowing_photo');
    expect(event['operation'], 'prepare');
    expect(event.toString(), isNot(contains('content_base64')));
    expect(payload['phase'], 'post_service');
    expect(payload['photo_scope'], 'mowing_demo_post_service_only');
    expect(payload['content_status'], 'not_uploaded');
    expect(payload['ruler_status'], 'not_validated');
    expect(payload['location_status'], 'not_collected');
    expect(payload['data_status'], 'simulated');
    expect(payload['quality_status'], 'simulated_unverified');
    expect(payload['operational_approval_satisfied'], isFalse);
    expect(payload['authorizes_field_work'], isFalse);
    expect(payload['eligible_for_field_execution'], isFalse);
    expect(payload['eligible_for_model_training'], isFalse);
    expect(payload['eligible_for_official_reporting'], isFalse);
  });

  test('rejects checksum corruption and promoted local labels', () {
    final corrupted = _draft().toJson()..['checksum_sha256'] = 'a' * 64;
    final promoted = _draft().toJson()
      ..['eligible_for_official_reporting'] = true;

    expect(
      () => MowingPostServicePhotoDraft.fromJson(corrupted),
      throwsFormatException,
    );
    expect(
      () => MowingPostServicePhotoDraft.fromJson(promoted),
      throwsFormatException,
    );
  });
}

MowingPostServicePhotoDraft _draft() {
  final bytes = Uint8List.fromList([0xff, 0xd8, 0xff, 0xd9]);
  return MowingPostServicePhotoDraft(
    eventId: '10000000-0000-4000-8000-000000000001',
    photoId: '10000000-0000-4000-8000-000000000002',
    mowingOrderId: '10000000-0000-4000-8000-000000000003',
    sourcePlanningApprovalId: '10000000-0000-4000-8000-000000000004',
    sourcePlannedPointId: '10000000-0000-4000-8000-000000000005',
    sequence: 1,
    capturedAt: DateTime.utc(2026, 8, 12, 14),
    checksumSha256: sha256.convert(bytes).toString(),
    mediaType: 'image/jpeg',
    bytes: bytes,
  );
}
