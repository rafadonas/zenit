import 'package:flutter/foundation.dart';

import 'data/offline_vault.dart';
import 'data/photo_capture.dart';
import 'data/device_identity_store.dart';
import 'data/secure_session_store.dart';
import 'data/zenit_gateway.dart';
import 'domain/auth_session.dart';
import 'domain/demo_order_lifecycle.dart';
import 'domain/measurement_draft.dart';
import 'domain/mobile_sync.dart';
import 'domain/mowing_demo_lifecycle.dart';
import 'domain/mowing_post_service_measurement_draft.dart';
import 'domain/mowing_post_service_photo_draft.dart';
import 'domain/prepared_mowing_plan.dart';
import 'domain/prepared_photo_draft.dart';
import 'domain/prepared_work_order.dart';

part 'core/mobile_workflow_errors.dart';
part 'features/inspection/application/inspection_workflow.dart';
part 'features/mowing_rehearsal/application/mowing_rehearsal_workflow.dart';

class ZenitAppController extends ChangeNotifier {
  ZenitAppController({
    required this.gateway,
    required this.sessionStore,
    required this.vault,
    required this.deviceIdentityStore,
    required this.appVersion,
    PhotoCapture? photoCapture,
    DateTime Function()? clock,
    String Function()? uuidFactory,
  }) : _clock = clock ?? DateTime.now,
       _uuidFactory = uuidFactory ?? generateUuidV4,
       _photoCapture = photoCapture ?? ImagePickerPhotoCapture();

  final ZenitGateway gateway;
  final SessionStore sessionStore;
  final OfflineVault vault;
  final DeviceIdentityStore deviceIdentityStore;
  final String appVersion;
  final DateTime Function() _clock;
  final String Function() _uuidFactory;
  final PhotoCapture _photoCapture;

  AuthSession? session;
  List<PreparedWorkOrder> orders = const [];
  List<PreparedMowingPlan> mowingPlans = const [];
  bool initializing = true;
  bool busy = false;
  String? errorMessage;

  bool get isAuthenticated => session != null;

  Future<void> initialize() async {
    try {
      await vault.initialize();
      orders = await vault.readOrders();
      mowingPlans = await vault.readMowingPlans();
      session = await sessionStore.readValid(_clock());
      if (session != null) {
        final ownerUserId = await vault.readOwnerUserId();
        if (ownerUserId != null && ownerUserId != session!.userId) {
          await _invalidateSession();
          errorMessage =
              'A sessão não corresponde ao proprietário dos dados criptografados.';
        } else {
          if (ownerUserId == null) {
            await vault.bindOwnerUserId(session!.userId);
          }
          await refreshOrders(silent: true);
        }
      } else {
        orders = const [];
        mowingPlans = const [];
      }
    } catch (error) {
      errorMessage = 'Falha ao abrir o armazenamento seguro: $error';
    } finally {
      initializing = false;
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    return _run(() async {
      final authenticated = await gateway.login(email, password);
      final downloaded = await _downloadPreparedSnapshots(
        authenticated.accessToken,
      );
      final ownerUserId = await vault.readOwnerUserId();
      if (ownerUserId != null && ownerUserId != authenticated.userId) {
        if (await vault.hasUnacknowledgedEvents()) {
          throw const LocalPendingEventsError();
        }
        await vault.clearUserData();
        await deviceIdentityStore.clear();
      }
      await vault.bindOwnerUserId(authenticated.userId);
      await vault.replaceOrders(downloaded.orders);
      await vault.replaceMowingPlans(downloaded.mowingPlans);
      await sessionStore.write(authenticated);
      session = authenticated;
      orders = await vault.readOrders();
      mowingPlans = await vault.readMowingPlans();
    });
  }

  Future<bool> refreshOrders({bool silent = false}) async {
    final current = session;
    if (current == null) return false;
    if (silent) {
      try {
        final downloaded = await _downloadPreparedSnapshots(
          current.accessToken,
        );
        await vault.replaceOrders(downloaded.orders);
        await vault.replaceMowingPlans(downloaded.mowingPlans);
        orders = await vault.readOrders();
        mowingPlans = await vault.readMowingPlans();
        notifyListeners();
        return true;
      } catch (error) {
        if (error is ZenitApiException && error.statusCode == 401) {
          await _invalidateSession();
        }
        return false;
      }
    }
    return _run(() async {
      final downloaded = await _downloadPreparedSnapshots(current.accessToken);
      await vault.replaceOrders(downloaded.orders);
      await vault.replaceMowingPlans(downloaded.mowingPlans);
      orders = await vault.readOrders();
      mowingPlans = await vault.readMowingPlans();
    });
  }

  Future<void> logout() async {
    final accessToken = session?.accessToken;
    String? logoutWarning;
    if (accessToken != null) {
      try {
        await gateway.logout(accessToken);
      } on Object {
        logoutWarning =
            'Sessão local encerrada; a revogação remota não pôde ser confirmada.';
      }
    }
    await _invalidateSession();
    errorMessage = logoutWarning;
    notifyListeners();
  }

  Future<void> _invalidateSession() async {
    await sessionStore.clear();
    session = null;
    orders = const [];
    mowingPlans = const [];
  }

  Future<
    ({List<PreparedWorkOrder> orders, List<PreparedMowingPlan> mowingPlans})
  >
  _downloadPreparedSnapshots(String accessToken) async {
    final downloadedOrders = await gateway.listPreparedOrders(accessToken);
    final downloadedMowingPlans = await gateway.listPreparedMowingPlans(
      accessToken,
    );
    return (orders: downloadedOrders, mowingPlans: downloadedMowingPlans);
  }

  Future<bool> _run(Future<void> Function() action) async {
    busy = true;
    errorMessage = null;
    notifyListeners();
    try {
      await action();
      return true;
    } catch (error) {
      if (error is ZenitApiException && error.statusCode == 401) {
        await _invalidateSession();
      }
      errorMessage = error is ZenitApiException
          ? error.message
          : error is MobileWorkflowException
          ? error.message
          : 'Operação não concluída: $error';
      return false;
    } finally {
      busy = false;
      notifyListeners();
    }
  }
}
