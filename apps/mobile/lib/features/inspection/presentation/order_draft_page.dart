import 'package:flutter/material.dart';

import '../../../app_controller.dart';
import '../../../core/presentation/field_banner.dart';
import '../../../core/presentation/field_card.dart';
import '../../../core/presentation/field_offline_indicator.dart';
import '../../../core/presentation/field_status_badge.dart';
import '../../../core/presentation/field_stepper.dart';
import '../../../core/presentation/field_tokens.dart';
import '../../../core/presentation/sync_status_view.dart';
import '../../../domain/demo_order_lifecycle.dart';
import '../../../domain/measurement_draft.dart';
import '../../../domain/prepared_photo_draft.dart';
import '../../../domain/prepared_work_order.dart';

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

  String get _nextActionText {
    if (lifecycle.isEmpty) {
      return 'Passo 1: Toque em "1. Confirmar" para preparar a ordem no aparelho.';
    }
    if (lifecycle.length == 1) {
      return 'Passo 2: Toque em "2. Iniciar (GPS simulado)" para simular a chegada ao segmento.';
    }
    if (lifecycle.length == 2) {
      final filledHeights = fields
          .where((f) => double.tryParse(f.text.replaceAll(',', '.')) != null)
          .length;
      if (filledHeights < 3 || drafts.length < 3) {
        return 'Passo 3: Digite as alturas dos 3 pontos e toque em "Salvar 3 rascunhos no aparelho".';
      }
      if (photos.length < 3) {
        return 'Passo 3: Capture a foto preparada dos pontos pendentes (${photos.length}/3 fotos registradas).';
      }
      return 'Passo 4: Toque em "3. Finalizar" para fechar a coleta local e habilitar a sincronização.';
    }
    if (lifecycle.length == 3) {
      final allAcknowledged = drafts.every(
        (d) => d.syncState == DraftSyncState.acknowledged,
      );
      if (!allAcknowledged) {
        return 'Passo 5: Toque em "Sincronizar lote preparado" para enviar eventos e manifestos.';
      }
      final allPhotosUploaded = photos.every((p) => p.isUploaded);
      if (!allPhotosUploaded) {
        return 'Passo 6: Manifestos aceitos. Toque em "Enviar fotos preparadas" para transferir os bytes.';
      }
      return 'Jornada concluída: eventos e fotos transmitidos (permanecem dados demonstrativos e não validados).';
    }
    return 'Revise o estado local do trecho.';
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text('${widget.order.roadCode} · ${widget.order.segmentIndex}'),
      actions: const [
        Padding(
          padding: EdgeInsets.only(right: FieldTokens.space3),
          child: Center(child: FieldOfflineIndicator(compact: true)),
        ),
      ],
    ),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(FieldTokens.space4),
            children: [
              const FieldBanner.critical(
                title: 'AMBIENTE DEMONSTRATIVO',
                message:
                    'Localização simulada · não comprova inspeção, não entra em relatório oficial e não autoriza roçada.',
              ),
              const SizedBox(height: FieldTokens.space3),
              FieldCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: FieldTokens.space2,
                      runSpacing: FieldTokens.space1,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        const Icon(
                          Icons.route,
                          color: FieldTokens.brand600,
                          size: 20,
                        ),
                        Text(
                          '${widget.order.roadCode} · segmento ${widget.order.segmentIndex}',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        FieldStatusBadge(
                          label: 'Zona ${widget.order.zoneType}',
                          icon: Icons.layers_outlined,
                          tone: FieldStatusTone.normal,
                          dense: true,
                        ),
                      ],
                    ),
                    const SizedBox(height: FieldTokens.space2),
                    Text(
                      widget.order.planningRationale,
                      style: const TextStyle(
                        color: FieldTokens.textMuted,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: FieldTokens.space3),
              FieldCard(
                backgroundColor: FieldTokens.canvas,
                borderColor: FieldTokens.brand600,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(
                      Icons.directions_walk,
                      color: FieldTokens.brand600,
                      size: 22,
                    ),
                    const SizedBox(width: FieldTokens.space2),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'PRÓXIMO PASSO DA JORNADA',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: FieldTokens.brand800,
                              letterSpacing: 0.5,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _nextActionText,
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: FieldTokens.text,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: FieldTokens.space3),
              FieldCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Progresso da Coleta',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: FieldTokens.space2),
                    FieldStepper(
                      steps: [
                        FieldStepItem(
                          stepNumber: 1,
                          title: 'Confirmar',
                          subtitle: lifecycle.isNotEmpty
                              ? 'Confirmado no aparelho'
                              : 'Pendente',
                          state: lifecycle.isNotEmpty
                              ? FieldStepState.complete
                              : FieldStepState.active,
                        ),
                        FieldStepItem(
                          stepNumber: 2,
                          title: 'Iniciar (GPS simulado)',
                          subtitle: lifecycle.length >= 2
                              ? 'Iniciado no trecho'
                              : (lifecycle.length == 1
                                    ? 'Aguardando início'
                                    : 'Bloqueado'),
                          state: lifecycle.length >= 2
                              ? FieldStepState.complete
                              : (lifecycle.length == 1
                                    ? FieldStepState.active
                                    : FieldStepState.disabled),
                        ),
                        FieldStepItem(
                          stepNumber: 3,
                          title: 'Finalizar',
                          subtitle: lifecycle.length >= 3
                              ? 'Coleta finalizada'
                              : (lifecycle.length == 2 &&
                                        drafts.length == 3 &&
                                        photos.length == 3
                                    ? 'Pronto para finalizar'
                                    : 'Aguardando 3 pontos e fotos'),
                          state: lifecycle.length >= 3
                              ? FieldStepState.complete
                              : (lifecycle.length == 2 &&
                                        drafts.length == 3 &&
                                        photos.length == 3
                                    ? FieldStepState.active
                                    : FieldStepState.disabled),
                        ),
                      ],
                    ),
                    const SizedBox(height: FieldTokens.space3),
                    Wrap(
                      spacing: FieldTokens.space2,
                      runSpacing: FieldTokens.space2,
                      children: [
                        OutlinedButton(
                          onPressed:
                              lifecycle.isEmpty &&
                                  !syncing &&
                                  !widget.controller.busy
                              ? () => _transition(
                                  widget.controller.confirmDemoOrder,
                                )
                              : null,
                          child: const Text('1. Confirmar'),
                        ),
                        OutlinedButton(
                          onPressed:
                              lifecycle.length == 1 &&
                                  !syncing &&
                                  !widget.controller.busy
                              ? () => _transition(
                                  widget.controller.startDemoOrder,
                                )
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
                              ? () => _transition(
                                  widget.controller.finishDemoOrder,
                                )
                              : null,
                          child: const Text('3. Finalizar'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (lifecycle.length >= 2) ...[
                const SizedBox(height: FieldTokens.space2),
                Row(
                  children: [
                    const Icon(
                      Icons.gps_fixed,
                      size: 16,
                      color: FieldTokens.statusAttentionText,
                    ),
                    const SizedBox(width: FieldTokens.space1),
                    Expanded(
                      child: Text(
                        'GPS simulado: ${lifecycle[1].simulatedLatitude}, '
                        '${lifecycle[1].simulatedLongitude} · prepared_point_demo_v1',
                        style: const TextStyle(
                          fontSize: 12,
                          color: FieldTokens.textMuted,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: FieldTokens.space4),
              Text(
                'Registro dos 3 Pontos de Coleta',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: FieldTokens.space2),
              for (
                var index = 0;
                index < widget.order.points.length;
                index++
              ) ...[
                Builder(
                  builder: (context) {
                    final point = widget.order.points[index];
                    final matches = photos.where(
                      (photo) => photo.plannedPointId == point.id,
                    );
                    final photo = matches.isEmpty ? null : matches.single;
                    final currentDraft = drafts
                        .where((d) => d.plannedPointId == point.id)
                        .firstOrNull;
                    final heightVal = double.tryParse(
                      fields[index].text.replaceAll(',', '.'),
                    );

                    return Padding(
                      padding: const EdgeInsets.only(
                        bottom: FieldTokens.space3,
                      ),
                      child: FieldCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Wrap(
                              spacing: FieldTokens.space2,
                              runSpacing: FieldTokens.space1,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                Text(
                                  'Ponto ${index + 1} (${(point.positionFraction * 100).round()}% do segmento)',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 15,
                                  ),
                                ),
                                if (currentDraft != null)
                                  FieldStatusBadge.fromSyncState(
                                    currentDraft.syncState,
                                  )
                                else
                                  const FieldStatusBadge(
                                    label: 'Não salvo no cofre',
                                    icon: Icons.edit_note,
                                    tone: FieldStatusTone.unknown,
                                    dense: true,
                                  ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text(
                              'Localização estimada: ${point.latitude.toStringAsFixed(6)}, ${point.longitude.toStringAsFixed(6)}',
                              style: const TextStyle(
                                fontSize: 12,
                                color: FieldTokens.textMuted,
                              ),
                            ),
                            const SizedBox(height: FieldTokens.space2),
                            TextField(
                              controller: fields[index],
                              readOnly:
                                  syncing || !canEdit || lifecycle.length != 2,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                    decimal: true,
                                  ),
                              decoration: InputDecoration(
                                labelText: 'Ponto ${index + 1} · altura (cm)',
                                helperText:
                                    '${(widget.order.points[index].positionFraction * 100).round()}% do segmento · localização estimada',
                              ),
                              onChanged: (_) => setState(() {}),
                            ),
                            if (heightVal != null) ...[
                              const SizedBox(height: FieldTokens.space1),
                              FieldStatusBadge.fromVegetationHeight(heightVal),
                            ],
                            const SizedBox(height: FieldTokens.space2),
                            OutlinedButton.icon(
                              onPressed:
                                  syncing ||
                                      widget.controller.busy ||
                                      lifecycle.length != 2 ||
                                      photo?.hasPersistentServerResult == true
                                  ? null
                                  : () => _capturePhoto(point),
                              icon: Icon(
                                photo == null
                                    ? Icons.camera_alt
                                    : Icons.verified,
                              ),
                              label: Text(
                                photo == null
                                    ? 'Capturar foto preparada do ponto ${index + 1}'
                                    : 'Foto ${photo.mediaType} · ${photo.bytes.length} bytes',
                              ),
                            ),
                            if (photo != null) ...[
                              const SizedBox(height: 4),
                              Wrap(
                                spacing: FieldTokens.space2,
                                runSpacing: FieldTokens.space1,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  FieldStatusBadge.fromSyncState(
                                    photo.syncState,
                                  ),
                                  Text(
                                    'SHA-256: ${photo.checksumSha256.substring(0, 12)}…',
                                    style: const TextStyle(
                                      fontSize: 11,
                                      color: FieldTokens.textMuted,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ],
                        ),
                      ),
                    );
                  },
                ),
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
                const SizedBox(height: FieldTokens.space4),
                FieldCard(
                  backgroundColor: FieldTokens.canvas,
                  borderColor: FieldTokens.borderStrong,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(
                            Icons.assignment_turned_in,
                            color: FieldTokens.brand600,
                          ),
                          SizedBox(width: FieldTokens.space2),
                          Expanded(
                            child: Text(
                              'Resumo da Coleta: Local vs Enviado',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 15,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: FieldTokens.space2),
                      Text(
                        'Cofre local: ${drafts.length}/3 alturas e ${photos.length}/3 fotos salvas com segurança no aparelho.',
                        style: const TextStyle(fontSize: 13),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Status de envio: ${drafts.where((d) => d.syncState == DraftSyncState.acknowledged).length}/3 confirmados no servidor · ${photos.where((p) => p.isUploaded).length}/3 fotos transferidas.',
                        style: const TextStyle(
                          fontSize: 13,
                          color: FieldTokens.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: FieldTokens.space3),
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
                  const SizedBox(height: FieldTokens.space2),
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
                const SizedBox(height: FieldTokens.space3),
                for (final event in lifecycle)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(syncIcon(event.syncState)),
                    title: Text(
                      '${_operationLabel(event.operation)}: '
                      '${syncLabel(event.syncState)}',
                    ),
                    subtitle: event.syncResultMessage == null
                        ? null
                        : Text(event.syncResultMessage!),
                  ),
                for (final draft in drafts)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(syncIcon(draft.syncState)),
                    title: Text(
                      'Ponto ${draft.sequence}: ${syncLabel(draft.syncState)}',
                    ),
                    subtitle: draft.syncResultMessage == null
                        ? null
                        : Text(draft.syncResultMessage!),
                  ),
                for (final photo in photos)
                  ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(syncIcon(photo.syncState)),
                    title: Text(
                      'Foto ${photo.sequence}: ${photo.isUploaded ? 'conteúdo recebido, não validado' : syncLabel(photo.syncState)}',
                    ),
                    subtitle: Text(
                      photo.syncResultMessage ??
                          'SHA-256 ${photo.checksumSha256.substring(0, 12)}… · não enviada · régua não validada',
                    ),
                  ),
              ],
              if (confirmation case final message?) ...[
                const SizedBox(height: FieldTokens.space3),
                FieldCard(
                  backgroundColor: FieldTokens.surface,
                  child: Row(
                    children: [
                      const Icon(
                        Icons.info_outline,
                        color: FieldTokens.brand600,
                        size: 20,
                      ),
                      const SizedBox(width: FieldTokens.space2),
                      Expanded(
                        child: Text(
                          message,
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: FieldTokens.space4),
              const Text(
                'O GPS exibido é simulado. Fotos enviadas permanecem preparadas e não validadas. Estes dados não comprovam inspeção, não entram em relatório oficial e não autorizam roçada.',
                style: TextStyle(
                  fontSize: 12,
                  color: FieldTokens.textMuted,
                  height: 1.4,
                ),
              ),
            ],
          ),
  );
}

String _operationLabel(DemoLifecycleOperation operation) => switch (operation) {
  DemoLifecycleOperation.confirm => 'Confirmação',
  DemoLifecycleOperation.start => 'Início simulado',
  DemoLifecycleOperation.finish => 'Finalização',
};
