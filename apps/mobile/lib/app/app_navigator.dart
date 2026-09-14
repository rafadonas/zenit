import 'package:flutter/material.dart';

import '../app_controller.dart';
import '../domain/prepared_mowing_plan.dart';
import '../domain/prepared_work_order.dart';
import '../features/inspection/presentation/order_draft_page.dart';
import '../features/mowing_rehearsal/presentation/prepared_mowing_plan_page.dart';

abstract final class AppNavigator {
  static Future<void> openInspectionDraft(
    BuildContext context, {
    required ZenitAppController controller,
    required PreparedWorkOrder order,
  }) => Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => OrderDraftPage(controller: controller, order: order),
    ),
  );

  static Future<void> openMowingPlan(
    BuildContext context, {
    required ZenitAppController controller,
    required PreparedMowingPlan plan,
  }) => Navigator.of(context).push(
    MaterialPageRoute(
      builder: (_) => PreparedMowingPlanPage(
        controller: controller,
        plan: plan,
      ),
    ),
  );
}
