import 'package:flutter/material.dart';

import '../app_controller.dart';
import '../features/auth/login_page.dart';
import '../features/work_orders/orders_page.dart';

class ZenitApp extends StatelessWidget {
  const ZenitApp({super.key, required this.controller});

  final ZenitAppController controller;

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'ZENIT Campo',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff125f4a)),
      useMaterial3: true,
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
      ),
    ),
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
