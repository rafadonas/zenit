import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/domain/mowing_demo_lifecycle.dart';

void main() {
  test('round-trips a safely labelled simulated mowing start', () {
    final event = MowingDemoLifecycleEvent(
      eventId: '10000000-0000-4000-8000-000000000001',
      mowingOrderId: '10000000-0000-4000-8000-000000000002',
      sourcePlanningApprovalId: '10000000-0000-4000-8000-000000000003',
      operation: MowingDemoOperation.start,
      occurredAt: DateTime.utc(2026, 8, 11, 14),
      simulatedLatitude: -23.5,
      simulatedLongitude: -46.6,
    );

    final restored = MowingDemoLifecycleEvent.fromJson(event.toJson());
    final payload = (event.toSyncEventJson()['payload']! as Map)
        .cast<String, Object?>();

    expect(restored.operation, MowingDemoOperation.start);
    expect(restored.simulatedLatitude, -23.5);
    expect(payload['data_status'], 'simulated');
    expect(payload['simulation_scope'], 'demo_only');
    expect(payload['rehearsal_scope'], 'mowing_demo_rehearsal_only');
    expect(payload['location_status'], 'simulated');
    expect(payload['simulation_method'], 'prepared_point_demo_v1');
    expect(payload['operational_approval_satisfied'], isFalse);
    expect(payload['authorizes_field_work'], isFalse);
    expect(payload['eligible_for_field_execution'], isFalse);
    expect(payload['eligible_for_model_training'], isFalse);
    expect(payload['eligible_for_official_reporting'], isFalse);
  });

  test('non-start events explicitly collect no location', () {
    final event = MowingDemoLifecycleEvent(
      eventId: '10000000-0000-4000-8000-000000000001',
      mowingOrderId: '10000000-0000-4000-8000-000000000002',
      sourcePlanningApprovalId: '10000000-0000-4000-8000-000000000003',
      operation: MowingDemoOperation.pause,
      occurredAt: DateTime.utc(2026, 8, 11, 14),
    );
    final payload = (event.toSyncEventJson()['payload']! as Map)
        .cast<String, Object?>();

    expect(payload['location_status'], 'not_collected');
    expect(payload.containsKey('simulated_latitude'), isFalse);
    expect(payload.containsKey('simulated_longitude'), isFalse);
  });

  test('rejects a locally persisted operational promotion', () {
    final json = MowingDemoLifecycleEvent(
      eventId: '10000000-0000-4000-8000-000000000001',
      mowingOrderId: '10000000-0000-4000-8000-000000000002',
      sourcePlanningApprovalId: '10000000-0000-4000-8000-000000000003',
      operation: MowingDemoOperation.confirm,
      occurredAt: DateTime.utc(2026, 8, 11, 14),
    ).toJson()..['authorizes_field_work'] = true;

    expect(
      () => MowingDemoLifecycleEvent.fromJson(json),
      throwsFormatException,
    );
  });

  test('refuses to serialize a start without a simulated point', () {
    final event = MowingDemoLifecycleEvent(
      eventId: '10000000-0000-4000-8000-000000000001',
      mowingOrderId: '10000000-0000-4000-8000-000000000002',
      sourcePlanningApprovalId: '10000000-0000-4000-8000-000000000003',
      operation: MowingDemoOperation.start,
      occurredAt: DateTime.utc(2026, 8, 11, 14),
    );

    expect(event.toSyncEventJson, throwsStateError);
    expect(event.toJson, throwsStateError);
  });
}
