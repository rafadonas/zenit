import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/domain/mowing_post_service_measurement_draft.dart';

void main() {
  test('round-trips a safely labelled simulated post-service measurement', () {
    final draft = _draft();

    final restored = MowingPostServiceMeasurementDraft.fromJson(draft.toJson());
    final event = draft.toSyncEventJson();
    final payload = (event['payload']! as Map).cast<String, Object?>();

    expect(restored.heightCm, 7.5);
    expect(event['entity_type'], 'mowing_measurement');
    expect(event['operation'], 'create');
    expect(payload['phase'], 'post_service');
    expect(payload['measurement_scope'], 'mowing_demo_post_service_only');
    expect(payload['location_status'], 'not_collected');
    expect(payload['photo_status'], 'not_collected');
    expect(payload['data_status'], 'simulated');
    expect(payload['quality_status'], 'simulated_unverified');
    expect(payload['operational_approval_satisfied'], isFalse);
    expect(payload['authorizes_field_work'], isFalse);
    expect(payload['eligible_for_field_execution'], isFalse);
    expect(payload['eligible_for_model_training'], isFalse);
    expect(payload['eligible_for_official_reporting'], isFalse);
  });

  test('rejects a locally persisted official-reporting promotion', () {
    final json = _draft().toJson()..['eligible_for_official_reporting'] = true;

    expect(
      () => MowingPostServiceMeasurementDraft.fromJson(json),
      throwsFormatException,
    );
  });

  test('refuses to serialize an invalid vegetation height', () {
    final draft = MowingPostServiceMeasurementDraft(
      eventId: '10000000-0000-4000-8000-000000000001',
      mowingOrderId: '10000000-0000-4000-8000-000000000002',
      sourcePlanningApprovalId: '10000000-0000-4000-8000-000000000003',
      sourcePlannedPointId: '10000000-0000-4000-8000-000000000004',
      sequence: 1,
      heightCm: double.nan,
      capturedAt: DateTime.utc(2026, 8, 12, 14),
    );

    expect(draft.toSyncEventJson, throwsStateError);
    expect(draft.toJson, throwsStateError);
  });
}

MowingPostServiceMeasurementDraft _draft() => MowingPostServiceMeasurementDraft(
  eventId: '10000000-0000-4000-8000-000000000001',
  mowingOrderId: '10000000-0000-4000-8000-000000000002',
  sourcePlanningApprovalId: '10000000-0000-4000-8000-000000000003',
  sourcePlannedPointId: '10000000-0000-4000-8000-000000000004',
  sequence: 1,
  heightCm: 7.5,
  capturedAt: DateTime.utc(2026, 8, 12, 14),
);
