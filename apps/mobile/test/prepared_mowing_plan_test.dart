import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/domain/prepared_mowing_plan.dart';

import 'support/fakes.dart';

void main() {
  test('accepts and round-trips a read-only prepared mowing plan', () {
    final plan = PreparedMowingPlan.fromJson(preparedMowingPlanJson());
    final restored = PreparedMowingPlan.fromJson(plan.toJson());

    expect(restored.id, plan.id);
    expect(restored.teamReference, 'TEAM-CANDIDATE-01');
    expect(restored.weatherResult, 'clear');
    expect(restored.safetyResult, 'clear');
    expect(restored.planningDecision, 'approved_for_planning');
    expect(restored.canConfirm, isFalse);
    expect(restored.canStart, isFalse);
    expect(restored.canTrack, isFalse);
    expect(restored.canFinish, isFalse);
    expect(restored.operationalApprovalSatisfied, isFalse);
    expect(restored.canRunDemoRehearsal, isTrue);
  });

  for (final field in [
    'operational_approval_satisfied',
    'authorizes_field_work',
    'eligible_for_field_execution',
    'eligible_for_model_training',
    'eligible_for_official_reporting',
  ]) {
    test('rejects promoted safety flag $field', () {
      final json = preparedMowingPlanJson()..[field] = true;

      expect(() => PreparedMowingPlan.fromJson(json), throwsFormatException);
    });
  }

  test('rejects readiness linked to a different resource plan', () {
    final json = preparedMowingPlanJson()
      ..['latest_readiness_resource_plan_id'] =
          '90000000-0000-4000-8000-000000000099';

    expect(() => PreparedMowingPlan.fromJson(json), throwsFormatException);
  });

  test('rejects planning decision linked to a stale readiness record', () {
    final json = preparedMowingPlanJson()
      ..['latest_planning_approval_readiness_id'] =
          '90000000-0000-4000-8000-000000000099';

    expect(() => PreparedMowingPlan.fromJson(json), throwsFormatException);
  });
}
