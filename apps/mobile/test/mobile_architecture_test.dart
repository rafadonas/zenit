import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('central mobile files remain focused on bootstrap and shared state', () {
    final mainSource = File('lib/main.dart').readAsStringSync();
    final controllerSource = File('lib/app_controller.dart').readAsStringSync();

    expect(mainSource.split('\n'), hasLength(lessThan(80)));
    expect(controllerSource.split('\n'), hasLength(lessThan(260)));

    for (final pageClass in [
      'class LoginPage',
      'class OrdersPage',
      'class OrderDraftPage',
      'class PreparedMowingPlanPage',
    ]) {
      expect(mainSource, isNot(contains(pageClass)));
    }

    for (final featureOperation in [
      'confirmDemoOrder',
      'syncPreparedDrafts',
      'confirmMowingDemo',
      'syncMowingDemo',
    ]) {
      expect(controllerSource, isNot(contains(featureOperation)));
    }
  });

  test('feature modules preserve the inspection and mowing boundaries', () {
    final inspectionSource = File(
      'lib/features/inspection/application/inspection_workflow.dart',
    ).readAsStringSync();
    final mowingSource = File(
      'lib/features/mowing_rehearsal/application/mowing_rehearsal_workflow.dart',
    ).readAsStringSync();

    expect(
      inspectionSource,
      contains('extension InspectionWorkflowController'),
    );
    expect(inspectionSource, contains('syncPreparedDrafts'));
    expect(inspectionSource, isNot(contains('confirmMowingDemo')));

    expect(
      mowingSource,
      contains('extension MowingRehearsalWorkflowController'),
    );
    expect(mowingSource, contains('syncMowingDemo'));
    expect(mowingSource, isNot(contains('confirmDemoOrder')));
  });
}
