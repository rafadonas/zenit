import 'package:flutter/material.dart';

import 'app_controller.dart';
import 'data/device_identity_store.dart';
import 'data/offline_vault.dart';
import 'data/secure_session_store.dart';
import 'data/zenit_gateway.dart';
import 'domain/demo_order_lifecycle.dart';
import 'domain/measurement_draft.dart';
import 'domain/prepared_photo_draft.dart';
import 'domain/prepared_work_order.dart';

const apiBaseUrl = String.fromEnvironment(
  'ZENIT_API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);
const mobileAppVersion = String.fromEnvironment(
  'ZENIT_APP_VERSION',
  defaultValue: '1.0.0+1',
);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final controller = ZenitAppController(
    gateway: HttpZenitGateway(baseUrl: apiBaseUrl),
    sessionStore: SecureSessionStore(),
    vault: HiveOfflineVault(),
    deviceIdentityStore: SecureDeviceIdentityStore(),
    appVersion: mobileAppVersion,
  );
  runApp(ZenitApp(controller: controller));
  controller.initialize();
}

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

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.controller});
  final ZenitAppController controller;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final email = TextEditingController();
  final password = TextEditingController();

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: SafeArea(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Icon(
                  Icons.landscape,
                  size: 64,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(height: 12),
                Text(
                  'ZENIT Campo',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Acesso inicial on-line. A senha nunca é armazenada.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                TextField(
                  controller: email,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.username],
                  decoration: const InputDecoration(labelText: 'E-mail'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: password,
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  decoration: const InputDecoration(labelText: 'Senha'),
                ),
                if (widget.controller.errorMessage case final message?) ...[
                  const SizedBox(height: 12),
                  Text(
                    message,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: widget.controller.busy
                      ? null
                      : () =>
                            widget.controller.login(email.text, password.text),
                  child: widget.controller.busy
                      ? const SizedBox.square(
                          dimension: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Entrar e baixar ordens'),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

class OrdersPage extends StatelessWidget {
  const OrdersPage({super.key, required this.controller});
  final ZenitAppController controller;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Ordens preparadas'),
      actions: [
        IconButton(
          onPressed: controller.busy ? null : controller.refreshOrders,
          tooltip: 'Atualizar',
          icon: const Icon(Icons.sync),
        ),
        IconButton(
          onPressed: controller.logout,
          tooltip: 'Sair; dados pendentes permanecem criptografados',
          icon: const Icon(Icons.logout),
        ),
      ],
    ),
    body: RefreshIndicator(
      onRefresh: controller.refreshOrders,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: const Padding(
              padding: EdgeInsets.all(16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.warning_amber_rounded),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'NÃO AUTORIZA TRABALHO DE CAMPO. Pontos e medições deste app são preparados, locais e inelegíveis para relatório oficial.',
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (controller.errorMessage case final message?) ...[
            const SizedBox(height: 8),
            Text(
              message,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          if (controller.orders.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 48),
              child: Center(child: Text('Nenhuma ordem preparada disponível.')),
            ),
          for (final order in controller.orders)
            Card(
              child: ListTile(
                leading: const CircleAvatar(child: Icon(Icons.route)),
                title: Text(
                  '${order.roadCode} · segmento ${order.segmentIndex}',
                ),
                subtitle: Text(
                  'Zona ${order.zoneType} · 3 pontos · somente rascunho',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) =>
                        OrderDraftPage(controller: controller, order: order),
                  ),
                ),
              ),
            ),
        ],
      ),
    ),
  );
}

class OrderDraftPage extends StatefulWidget {
  const OrderDraftPage({
    super.key,
    required this.controller,
    required this.order,
  });
  final ZenitAppController controller;
  final PreparedWorkOrder order;

  @override
  State<OrderDraftPage> createState() => _OrderDraftPageState();
}

class _OrderDraftPageState extends State<OrderDraftPage> {
  final fields = List.generate(3, (_) => TextEditingController());
  bool loading = true;
  bool syncing = false;
  String? confirmation;
  List<MeasurementDraft> drafts = const [];
  List<DemoLifecycleEvent> lifecycle = const [];
  List<PreparedPhotoDraft> photos = const [];

  bool get canEdit =>
      drafts.every((draft) => draft.syncState == DraftSyncState.localOnly);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final loadedDrafts = await widget.controller.readDrafts(widget.order.id);
    final loadedLifecycle = await widget.controller.readLifecycleEvents(
      widget.order.id,
    );
    final loadedPhotos = await widget.controller.readPhotoDrafts(
      widget.order.id,
    );
    if (!mounted) return;
    for (
      var index = 0;
      index < loadedDrafts.length && index < fields.length;
      index++
    ) {
      fields[index].text = loadedDrafts[index].heightCm.toString();
    }
    setState(() {
      drafts = loadedDrafts;
      lifecycle = loadedLifecycle;
      photos = loadedPhotos;
      loading = false;
    });
  }

  @override
  void dispose() {
    for (final field in fields) {
      field.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    final heights = fields
        .map((field) => double.tryParse(field.text.replaceAll(',', '.')))
        .toList();
    if (heights.any((height) => height == null)) {
      setState(() => confirmation = 'Preencha as três alturas.');
      return;
    }
    final saved = await widget.controller.saveThreeDrafts(
      widget.order,
      heights.cast<double>(),
    );
    if (mounted) {
      if (saved) await _load();
      if (!mounted) return;
      setState(
        () => confirmation = saved
            ? 'Três eventos preparados e criptografados no aparelho.'
            : widget.controller.errorMessage,
      );
    }
  }

  Future<void> _sync() async {
    setState(() => syncing = true);
    final synced = await widget.controller.syncPreparedDrafts(widget.order);
    if (!mounted) return;
    await _load();
    if (!mounted) return;
    final states = [
      ...lifecycle.map((event) => event.syncState),
      ...drafts.map((draft) => draft.syncState),
      ...photos.map((photo) => photo.syncState),
    ];
    final acknowledged = states
        .where((state) => state == DraftSyncState.acknowledged)
        .length;
    final rejected = states
        .where((state) => state == DraftSyncState.rejected)
        .length;
    final conflicts = states
        .where((state) => state == DraftSyncState.conflict)
        .length;
    setState(() {
      syncing = false;
      confirmation = synced
          ? 'Resultado persistido: $acknowledged aceitos, $rejected rejeitados, $conflicts conflitos.'
          : widget.controller.errorMessage;
    });
  }

  Future<void> _transition(
    Future<bool> Function(PreparedWorkOrder) action,
  ) async {
    final changed = await action(widget.order);
    if (!mounted) return;
    if (changed) await _load();
    if (!mounted) return;
    setState(
      () => confirmation = changed
          ? 'Evento demonstrativo criptografado no aparelho.'
          : widget.controller.errorMessage,
    );
  }

  Future<void> _capturePhoto(PlannedInspectionPoint point) async {
    final captured = await widget.controller.capturePreparedPhoto(
      widget.order,
      point,
    );
    if (!mounted) return;
    if (captured) await _load();
    if (!mounted) return;
    setState(
      () => confirmation = captured
          ? 'Foto copiada para o vault criptografado; conteúdo não enviado.'
          : widget.controller.errorMessage,
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text('${widget.order.roadCode} · ${widget.order.segmentIndex}'),
    ),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text(
                'Rascunho offline preparado',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              Text(widget.order.planningRationale),
              const SizedBox(height: 12),
              const Text(
                'AMBIENTE DEMONSTRATIVO · localização simulada',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton(
                    onPressed:
                        lifecycle.isEmpty && !syncing && !widget.controller.busy
                        ? () => _transition(widget.controller.confirmDemoOrder)
                        : null,
                    child: const Text('1. Confirmar'),
                  ),
                  OutlinedButton(
                    onPressed:
                        lifecycle.length == 1 &&
                            !syncing &&
                            !widget.controller.busy
                        ? () => _transition(widget.controller.startDemoOrder)
                        : null,
                    child: const Text('2. Iniciar (GPS simulado)'),
                  ),
                  OutlinedButton(
                    onPressed:
                        lifecycle.length == 2 &&
                            drafts.length == 3 &&
                            photos.length == 3 &&
                            !syncing &&
                            !widget.controller.busy
                        ? () => _transition(widget.controller.finishDemoOrder)
                        : null,
                    child: const Text('3. Finalizar'),
                  ),
                ],
              ),
              if (lifecycle.length >= 2) ...[
                const SizedBox(height: 8),
                Text(
                  'GPS simulado: ${lifecycle[1].simulatedLatitude}, '
                  '${lifecycle[1].simulatedLongitude} · prepared_point_demo_v1',
                ),
              ],
              const SizedBox(height: 16),
              for (
                var index = 0;
                index < widget.order.points.length;
                index++
              ) ...[
                TextField(
                  controller: fields[index],
                  readOnly: syncing || !canEdit || lifecycle.length != 2,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: InputDecoration(
                    labelText: 'Ponto ${index + 1} · altura (cm)',
                    helperText:
                        '${(widget.order.points[index].positionFraction * 100).round()}% do segmento · localização estimada',
                  ),
                ),
                const SizedBox(height: 6),
                Builder(
                  builder: (context) {
                    final point = widget.order.points[index];
                    final matches = photos.where(
                      (photo) => photo.plannedPointId == point.id,
                    );
                    final photo = matches.isEmpty ? null : matches.single;
                    return OutlinedButton.icon(
                      onPressed:
                          syncing ||
                              widget.controller.busy ||
                              lifecycle.length != 2 ||
                              photo?.hasPersistentServerResult == true
                          ? null
                          : () => _capturePhoto(point),
                      icon: Icon(
                        photo == null ? Icons.camera_alt : Icons.verified,
                      ),
                      label: Text(
                        photo == null
                            ? 'Capturar foto preparada do ponto ${index + 1}'
                            : 'Foto ${photo.mediaType} · ${photo.bytes.length} bytes',
                      ),
                    );
                  },
                ),
                const SizedBox(height: 14),
              ],
              FilledButton.icon(
                onPressed:
                    syncing ||
                        widget.controller.busy ||
                        !canEdit ||
                        lifecycle.length != 2
                    ? null
                    : _save,
                icon: const Icon(Icons.lock),
                label: const Text('Salvar 3 rascunhos no aparelho'),
              ),
              if (drafts.length == 3 && lifecycle.length == 3) ...[
                const SizedBox(height: 10),
                OutlinedButton.icon(
                  onPressed:
                      syncing ||
                          widget.controller.busy ||
                          drafts.every(
                            (draft) => draft.hasPersistentServerResult,
                          )
                      ? null
                      : _sync,
                  icon: const Icon(Icons.sync),
                  label: const Text('Sincronizar lote preparado'),
                ),
                if (photos.every(
                  (photo) => photo.syncState == DraftSyncState.acknowledged,
                )) ...[
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed:
                        syncing ||
                            widget.controller.busy ||
                            photos.every((photo) => photo.isUploaded)
                        ? null
                        : () => _transition(
                            widget.controller.uploadPreparedPhotos,
                          ),
                    icon: const Icon(Icons.cloud_upload),
                    label: const Text('Enviar fotos preparadas'),
                  ),
                ],
                const SizedBox(height: 12),
                for (final event in lifecycle)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(_syncIcon(event.syncState)),
                    title: Text(
                      '${_operationLabel(event.operation)}: '
                      '${_syncLabel(event.syncState)}',
                    ),
                    subtitle: event.syncResultMessage == null
                        ? null
                        : Text(event.syncResultMessage!),
                  ),
                for (final draft in drafts)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(_syncIcon(draft.syncState)),
                    title: Text(
                      'Ponto ${draft.sequence}: ${_syncLabel(draft.syncState)}',
                    ),
                    subtitle: draft.syncResultMessage == null
                        ? null
                        : Text(draft.syncResultMessage!),
                  ),
                for (final photo in photos)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(_syncIcon(photo.syncState)),
                    title: Text(
                      'Foto ${photo.sequence}: ${photo.isUploaded ? 'conteúdo recebido, não validado' : _syncLabel(photo.syncState)}',
                    ),
                    subtitle: Text(
                      photo.syncResultMessage ??
                          'SHA-256 ${photo.checksumSha256.substring(0, 12)}… · não enviada · régua não validada',
                    ),
                  ),
              ],
              if (confirmation case final message?) ...[
                const SizedBox(height: 12),
                Text(message),
              ],
              const SizedBox(height: 20),
              const Text(
                'O GPS exibido é simulado. Fotos enviadas permanecem preparadas e não validadas. Estes dados não comprovam inspeção, não entram em relatório oficial e não autorizam roçada.',
              ),
            ],
          ),
  );
}

String _syncLabel(DraftSyncState state) => switch (state) {
  DraftSyncState.localOnly => 'somente local',
  DraftSyncState.pending => 'aguardando confirmação',
  DraftSyncState.acknowledged => 'persistido no servidor',
  DraftSyncState.rejected => 'rejeitado pelo servidor',
  DraftSyncState.conflict => 'conflito preservado',
};

String _operationLabel(DemoLifecycleOperation operation) => switch (operation) {
  DemoLifecycleOperation.confirm => 'Confirmação',
  DemoLifecycleOperation.start => 'Início simulado',
  DemoLifecycleOperation.finish => 'Finalização',
};

IconData _syncIcon(DraftSyncState state) => switch (state) {
  DraftSyncState.localOnly => Icons.phone_android,
  DraftSyncState.pending => Icons.sync,
  DraftSyncState.acknowledged => Icons.cloud_done,
  DraftSyncState.rejected => Icons.cloud_off,
  DraftSyncState.conflict => Icons.warning_amber,
};
