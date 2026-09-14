import 'package:flutter/material.dart';

import '../../../app_controller.dart';
import '../../../core/presentation/read_only_value.dart';
import '../../../core/presentation/sync_status_view.dart';
import '../../../domain/measurement_draft.dart';
import '../../../domain/mowing_demo_lifecycle.dart';
import '../../../domain/mowing_post_service_measurement_draft.dart';
import '../../../domain/mowing_post_service_photo_draft.dart';
import '../../../domain/prepared_mowing_plan.dart';
import '../../../domain/prepared_work_order.dart';

class PreparedMowingPlanPage extends StatefulWidget {
  const PreparedMowingPlanPage({
    super.key,
    required this.controller,
    required this.plan,
  });

  final ZenitAppController controller;
  final PreparedMowingPlan plan;

  @override
  State<PreparedMowingPlanPage> createState() => _PreparedMowingPlanPageState();
}

class _PreparedMowingPlanPageState extends State<PreparedMowingPlanPage> {
  final postServiceFields = List.generate(3, (_) => TextEditingController());
  bool loading = true;
  bool syncing = false;
  String? confirmation;
  List<MowingDemoLifecycleEvent> events = const [];
  List<MowingPostServiceMeasurementDraft> measurements = const [];
  List<MowingPostServicePhotoDraft> photos = const [];

  PreparedMowingPlan get plan => widget.plan;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final loaded = await widget.controller.readMowingLifecycleEvents(plan.id);
    final loadedMeasurements = await widget.controller
        .readMowingPostServiceMeasurements(plan.id);
    final loadedPhotos = await widget.controller.readMowingPostServicePhotos(
      plan.id,
    );
    if (!mounted) return;
    for (final measurement in loadedMeasurements) {
      postServiceFields[measurement.sequence - 1].text = measurement.heightCm
          .toString();
    }
    setState(() {
      events = loaded;
      measurements = loadedMeasurements;
      photos = loadedPhotos;
      loading = false;
    });
  }

  @override
  void dispose() {
    for (final field in postServiceFields) {
      field.dispose();
    }
    super.dispose();
  }

  bool get canEditPostServiceMeasurements =>
      events.isNotEmpty &&
      events.last.operation == MowingDemoOperation.finish &&
      events.every(
        (event) => const {
          DraftSyncState.localOnly,
          DraftSyncState.acknowledged,
        }.contains(event.syncState),
      ) &&
      measurements.every(
        (measurement) => measurement.syncState == DraftSyncState.localOnly,
      ) &&
      photos.isEmpty;

  PreparedWorkOrder? get sourceOrder => widget.controller.orders
      .where((order) => order.id == plan.sourceInspectionWorkOrderId)
      .firstOrNull;

  bool get canCapturePostServicePhotos =>
      measurements.length == 3 &&
      measurements.every(
        (measurement) => const {
          DraftSyncState.localOnly,
          DraftSyncState.acknowledged,
        }.contains(measurement.syncState),
      );

  Future<void> _transition(
    Future<bool> Function(PreparedMowingPlan) action,
  ) async {
    final changed = await action(plan);
    if (!mounted) return;
    if (changed) await _load();
    if (!mounted) return;
    setState(
      () => confirmation = changed
          ? 'Evento de ensaio simulado criptografado no aparelho.'
          : widget.controller.errorMessage,
    );
  }

  Future<void> _sync() async {
    setState(() => syncing = true);
    final synced = await widget.controller.syncMowingDemo(plan);
    if (!mounted) return;
    await _load();
    if (!mounted) return;
    final acknowledged =
        events
            .where((event) => event.syncState == DraftSyncState.acknowledged)
            .length +
        measurements
            .where((item) => item.syncState == DraftSyncState.acknowledged)
            .length +
        photos
            .where((photo) => photo.syncState == DraftSyncState.acknowledged)
            .length;
    final rejected =
        events
            .where((event) => event.syncState == DraftSyncState.rejected)
            .length +
        measurements
            .where((item) => item.syncState == DraftSyncState.rejected)
            .length +
        photos
            .where((photo) => photo.syncState == DraftSyncState.rejected)
            .length;
    final conflicts =
        events
            .where((event) => event.syncState == DraftSyncState.conflict)
            .length +
        measurements
            .where((item) => item.syncState == DraftSyncState.conflict)
            .length +
        photos
            .where((photo) => photo.syncState == DraftSyncState.conflict)
            .length;
    setState(() {
      syncing = false;
      confirmation = synced
          ? 'Ensaio, medições e manifestos: $acknowledged aceitos, $rejected rejeitados, $conflicts conflitos.'
          : widget.controller.errorMessage;
    });
  }

  Future<void> _uploadPostServicePhotos() async {
    setState(() => syncing = true);
    final uploaded = await widget.controller.uploadMowingPostServicePhotos(
      plan,
    );
    if (!mounted) return;
    await _load();
    if (!mounted) return;
    final uploadedCount = photos.where((photo) => photo.isUploaded).length;
    setState(() {
      syncing = false;
      confirmation = uploaded
          ? '$uploadedCount fotos simuladas recebidas e criptografadas; conteúdo não validado.'
          : widget.controller.errorMessage;
    });
  }

  Future<void> _savePostServiceMeasurements() async {
    final heights = postServiceFields
        .map((field) => double.tryParse(field.text.replaceAll(',', '.')))
        .toList();
    if (heights.any((height) => height == null)) {
      setState(() => confirmation = 'Preencha as três alturas pós-serviço.');
      return;
    }
    final saved = await widget.controller
        .saveThreeMowingPostServiceMeasurements(plan, heights.cast<double>());
    if (!mounted) return;
    if (saved) await _load();
    if (!mounted) return;
    setState(
      () => confirmation = saved
          ? 'Três medições pós-serviço simuladas foram criptografadas no aparelho.'
          : widget.controller.errorMessage,
    );
  }

  Future<void> _capturePostServicePhoto(PlannedInspectionPoint point) async {
    final captured = await widget.controller.captureMowingPostServicePhoto(
      plan,
      point,
    );
    if (!mounted) return;
    if (captured) await _load();
    if (!mounted) return;
    setState(
      () => confirmation = captured
          ? 'Foto pós-serviço simulada criptografada; conteúdo não enviado.'
          : widget.controller.errorMessage,
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Planejamento de roçada')),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Card(
                color: Theme.of(context).colorScheme.errorContainer,
                child: const Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.block),
                          SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'ENSAIO SIMULADO — NÃO É EXECUÇÃO',
                              style: TextStyle(fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Os controles registram apenas um ensaio. Não há despacho, GPS real, rastreamento, serviço de campo ou aprovação operacional.',
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                '${plan.roadCode} · segmento ${plan.segmentIndex}',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 4),
              Text('Zona ${plan.zoneType} · localização simulada'),
              const SizedBox(height: 16),
              ReadOnlyValue(
                label: 'Justificativa',
                value: plan.planningRationale,
              ),
              ReadOnlyValue(
                label: 'Equipe candidata',
                value: plan.teamReference ?? 'Não planejada',
              ),
              ReadOnlyValue(
                label: 'Equipamento candidato',
                value: plan.equipmentReference ?? 'Não planejado',
              ),
              ReadOnlyValue(
                label: 'Clima (declaração manual)',
                value: _preparedMowingLabel(plan.weatherResult),
              ),
              ReadOnlyValue(
                label: 'Fonte do clima',
                value: plan.weatherSourceReference ?? 'Não avaliada',
              ),
              ReadOnlyValue(
                label: 'Segurança (declaração manual)',
                value: _preparedMowingLabel(plan.safetyResult),
              ),
              ReadOnlyValue(
                label: 'Fonte de segurança',
                value: plan.safetySourceReference ?? 'Não avaliada',
              ),
              ReadOnlyValue(
                label: 'Decisão de planejamento',
                value: _preparedMowingLabel(plan.planningDecision),
              ),
              ReadOnlyValue(
                label: 'Justificativa da decisão',
                value:
                    plan.planningDecisionRationale ?? 'Sem decisão registrada',
              ),
              ReadOnlyValue(
                label: 'Aprovação operacional',
                value: 'Não satisfeita',
              ),
              ReadOnlyValue(
                label: 'Proveniência',
                value:
                    'Revisão ${plan.sourceReviewState} · política ${plan.creationPolicyVersion}',
              ),
              const SizedBox(height: 8),
              Text(
                'Ciclo do ensaio offline',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              if (!plan.canRunDemoRehearsal)
                const Text(
                  'Bloqueado: exige revisão efetiva, clima e segurança declarados livres e aprovação somente para planejamento.',
                )
              else ...[
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton(
                      onPressed:
                          events.isEmpty && !syncing && !widget.controller.busy
                          ? () =>
                                _transition(widget.controller.confirmMowingDemo)
                          : null,
                      child: const Text('1. Confirmar ensaio'),
                    ),
                    OutlinedButton(
                      onPressed:
                          events.length == 1 &&
                              !syncing &&
                              !widget.controller.busy
                          ? () => _transition(widget.controller.startMowingDemo)
                          : null,
                      child: const Text('2. Iniciar (ponto simulado)'),
                    ),
                    OutlinedButton(
                      onPressed:
                          events.isNotEmpty &&
                              const {
                                MowingDemoOperation.start,
                                MowingDemoOperation.resume,
                              }.contains(events.last.operation) &&
                              !syncing &&
                              !widget.controller.busy
                          ? () => _transition(widget.controller.pauseMowingDemo)
                          : null,
                      child: const Text('Pausar ensaio'),
                    ),
                    OutlinedButton(
                      onPressed:
                          events.isNotEmpty &&
                              events.last.operation ==
                                  MowingDemoOperation.pause &&
                              !syncing &&
                              !widget.controller.busy
                          ? () =>
                                _transition(widget.controller.resumeMowingDemo)
                          : null,
                      child: const Text('Retomar ensaio'),
                    ),
                    OutlinedButton(
                      onPressed:
                          events.isNotEmpty &&
                              const {
                                MowingDemoOperation.start,
                                MowingDemoOperation.resume,
                              }.contains(events.last.operation) &&
                              !syncing &&
                              !widget.controller.busy
                          ? () =>
                                _transition(widget.controller.finishMowingDemo)
                          : null,
                      child: const Text('3. Finalizar ensaio'),
                    ),
                  ],
                ),
                if (events.any(
                  (event) => event.operation == MowingDemoOperation.start,
                )) ...[
                  const SizedBox(height: 8),
                  Builder(
                    builder: (context) {
                      final start = events.firstWhere(
                        (event) => event.operation == MowingDemoOperation.start,
                      );
                      return Text(
                        'Ponto simulado: ${start.simulatedLatitude}, ${start.simulatedLongitude} · prepared_point_demo_v1',
                      );
                    },
                  ),
                ],
                if (events.isNotEmpty &&
                    events.last.operation == MowingDemoOperation.finish) ...[
                  const SizedBox(height: 10),
                  Text(
                    'Medições pós-serviço simuladas',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Entrada digitada e não verificada. A medição não embute GPS ou foto; imagens ficam em evidência separada.',
                  ),
                  const SizedBox(height: 10),
                  for (
                    var index = 0;
                    index < postServiceFields.length;
                    index++
                  ) ...[
                    TextField(
                      controller: postServiceFields[index],
                      readOnly:
                          syncing ||
                          widget.controller.busy ||
                          !canEditPostServiceMeasurements,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: InputDecoration(
                        labelText:
                            'Ponto ${index + 1} · altura pós-serviço (cm)',
                        helperText:
                            'Mesmo ponto preparado da inspeção de origem · sem GPS',
                      ),
                    ),
                    const SizedBox(height: 10),
                  ],
                  FilledButton.icon(
                    onPressed:
                        syncing ||
                            widget.controller.busy ||
                            !canEditPostServiceMeasurements
                        ? null
                        : _savePostServiceMeasurements,
                    icon: const Icon(Icons.lock),
                    label: const Text('Salvar 3 medições simuladas'),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Fotos pós-serviço simuladas',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Os bytes ficam criptografados no aparelho. A sincronização envia apenas o manifesto; depois, um envio explícito transfere o conteúdo ainda simulado e não validado.',
                  ),
                  const SizedBox(height: 8),
                  if (sourceOrder case final PreparedWorkOrder order)
                    for (final point in order.points)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Icon(
                          photos.any(
                                (photo) =>
                                    photo.sourcePlannedPointId == point.id,
                              )
                              ? Icons.lock
                              : Icons.camera_alt_outlined,
                        ),
                        title: Text('Ponto ${point.sequence}'),
                        subtitle: Text(
                          photos
                                  .where(
                                    (photo) =>
                                        photo.sourcePlannedPointId == point.id,
                                  )
                                  .firstOrNull
                                  ?.syncResultMessage ??
                              'Sem GPS, régua não validada e conteúdo não enviado.',
                        ),
                        trailing: OutlinedButton(
                          onPressed:
                              syncing ||
                                  widget.controller.busy ||
                                  !canCapturePostServicePhotos ||
                                  photos.any(
                                    (photo) =>
                                        photo.sourcePlannedPointId ==
                                            point.id &&
                                        photo.hasPersistentServerResult,
                                  )
                              ? null
                              : () => _capturePostServicePhoto(point),
                          child: Text(
                            photos.any(
                                  (photo) =>
                                      photo.sourcePlannedPointId == point.id,
                                )
                                ? 'Refazer local'
                                : 'Capturar',
                          ),
                        ),
                      ),
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed:
                        syncing ||
                            widget.controller.busy ||
                            measurements.length != 3 ||
                            photos.length != 3 ||
                            photos.every(
                              (photo) => photo.hasPersistentServerResult,
                            )
                        ? null
                        : _sync,
                    icon: const Icon(Icons.sync),
                    label: const Text(
                      'Sincronizar medições e manifestos simulados',
                    ),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed:
                        syncing ||
                            widget.controller.busy ||
                            photos.length != 3 ||
                            photos.any(
                              (photo) =>
                                  photo.syncState !=
                                  DraftSyncState.acknowledged,
                            ) ||
                            photos.every((photo) => photo.isUploaded)
                        ? null
                        : _uploadPostServicePhotos,
                    icon: const Icon(Icons.cloud_upload),
                    label: const Text('Enviar fotos simuladas pós-serviço'),
                  ),
                ],
                for (final event in events)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(syncIcon(event.syncState)),
                    title: Text(
                      '${_mowingOperationLabel(event.operation)}: ${syncLabel(event.syncState)}',
                    ),
                    subtitle: event.syncResultMessage == null
                        ? null
                        : Text(event.syncResultMessage!),
                  ),
                for (final measurement in measurements)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(syncIcon(measurement.syncState)),
                    title: Text(
                      'Pós-serviço ${measurement.sequence}: ${measurement.heightCm} cm · ${syncLabel(measurement.syncState)}',
                    ),
                    subtitle: Text(
                      measurement.syncResultMessage ??
                          'Altura simulada sem GPS ou imagem embutida e não oficial.',
                    ),
                  ),
                for (final photo in photos)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      photo.isUploaded
                          ? Icons.cloud_done
                          : syncIcon(photo.syncState),
                    ),
                    title: Text(
                      'Foto pós-serviço ${photo.sequence}: ${photo.isUploaded ? 'conteúdo recebido, não validado' : syncLabel(photo.syncState)}',
                    ),
                    subtitle: Text(
                      photo.syncResultMessage ??
                          'Criptografada localmente, não enviada e não validada.',
                    ),
                  ),
              ],
              if (confirmation case final message?) ...[
                const SizedBox(height: 8),
                Text(message),
              ],
              const SizedBox(height: 16),
              const Text(
                'Todos os eventos e alturas pós-serviço são simulados, não verificados, inelegíveis para treinamento e relatório oficial, e nunca autorizam roçada.',
              ),
            ],
          ),
  );
}

String _preparedMowingLabel(String? value) => switch (value) {
  'clear' => 'Declarado livre — validação pendente',
  'blocked' => 'Declarado bloqueado',
  'inconclusive' => 'Inconclusivo',
  'approved_for_planning' => 'Aprovado somente para planejamento',
  'changes_requested' => 'Alterações solicitadas',
  'rejected' => 'Rejeitado',
  _ => 'Não registrado',
};

String _mowingOperationLabel(MowingDemoOperation operation) =>
    switch (operation) {
      MowingDemoOperation.confirm => 'Confirmação do ensaio',
      MowingDemoOperation.start => 'Início simulado',
      MowingDemoOperation.pause => 'Pausa do ensaio',
      MowingDemoOperation.resume => 'Retomada do ensaio',
      MowingDemoOperation.finish => 'Fim do ensaio',
    };
