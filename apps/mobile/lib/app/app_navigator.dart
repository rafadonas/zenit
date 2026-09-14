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
  }) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => OrderDraftPage(controller: controller, order: order),
      ),
    );
  }

  static Future<void> openMowingPlan(
    BuildContext context, {
    required ZenitAppController controller,
    required PreparedMowingPlan plan,
  }) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) =>
            PreparedMowingPlanPage(controller: controller, plan: plan),
      ),
    );
  }
}
