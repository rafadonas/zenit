import 'package:flutter/material.dart';

import '../app_controller.dart';
import '../core/presentation/field_theme.dart';
import '../features/auth/presentation/login_page.dart';
import '../features/work_orders/presentation/orders_page.dart';

class ZenitApp extends StatelessWidget {
  const ZenitApp({super.key, required this.controller});

  final ZenitAppController controller;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'ZENIT Campo',
    debugShowCheckedModeBanner: false,
    theme: FieldTheme.createTheme(),
    home: ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        if (controller.initializing) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        if (!controller.isAuthenticated) {
          return LoginPage(controller: controller);
        }
        return OrdersPage(controller: controller);
      },
    ),
  );
}
