import 'package:flutter/material.dart';

import 'app/zenit_app.dart';
import 'app_controller.dart';
import 'data/device_identity_store.dart';
import 'data/offline_vault.dart';
import 'data/secure_session_store.dart';
import 'data/zenit_gateway.dart';

export 'app/zenit_app.dart';
export 'features/auth/presentation/login_page.dart';
export 'features/inspection/presentation/order_draft_page.dart';
export 'features/mowing_rehearsal/presentation/prepared_mowing_plan_page.dart';
export 'features/work_orders/presentation/orders_page.dart';

const apiBaseUrl = String.fromEnvironment(
  'ZENIT_API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
const mobileAppVersion = String.fromEnvironment(
  'ZENIT_APP_VERSION',
  defaultValue: '1.0.0+1',
);
const apiRequestTimeoutSeconds = int.fromEnvironment(
  'ZENIT_API_REQUEST_TIMEOUT_SECONDS',
  defaultValue: defaultZenitApiRequestTimeoutSeconds,
);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final controller = ZenitAppController(
    gateway: HttpZenitGateway(
      baseUrl: apiBaseUrl,
      requestTimeout: const Duration(seconds: apiRequestTimeoutSeconds),
    ),
    sessionStore: SecureSessionStore(),
    vault: HiveOfflineVault(),
    deviceIdentityStore: SecureDeviceIdentityStore(),
    appVersion: mobileAppVersion,
  );
  runApp(ZenitApp(controller: controller));
  controller.initialize();
}
