import 'package:flutter/material.dart';

import '../../../app_controller.dart';
import '../../../domain/sync_center.dart';

class SyncCenterPage extends StatefulWidget {
  const SyncCenterPage({super.key, required this.controller});

  final ZenitAppController controller;

  @override
  State<SyncCenterPage> createState() => _SyncCenterPageState();
}

class _SyncCenterPageState extends State<SyncCenterPage> {
  late Future<List<SyncCenterItem>> items;
  String? runningKey;

  @override
  void initState() {
    super.initState();
    items = widget.controller.readSyncCenterItems();
  }

  Future<void> _reload() async {
    setState(() => items = widget.controller.readSyncCenterItems());
    await items;
  }

  Future<void> _retry(SyncCenterItem item) async {
    setState(() => runningKey = item.key);
    await widget.controller.retrySyncCenterItem(item);
    if (!mounted) return;
    setState(() {
      runningKey = null;
      items = widget.controller.readSyncCenterItems();
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Central de sincronização')),
    body: RefreshIndicator(
      onRefresh: _reload,
      child: FutureBuilder<List<SyncCenterItem>>(
        future: items,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return ListView(
              children: const [
                SizedBox(height: 240),
                Center(child: CircularProgressIndicator()),
              ],
            );
          }
          if (snapshot.hasError) {
            return ListView(
              padding: const EdgeInsets.all(24),
              children: const [
                Icon(Icons.sync_problem, size: 48),
                SizedBox(height: 12),
                Text(
                  'Não foi possível ler a fila criptografada. Tente novamente sem apagar os dados locais.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }
          final values = snapshot.data ?? const [];
          if (values.isEmpty) {
            return ListView(
              padding: const EdgeInsets.all(24),
              children: const [
                Icon(Icons.cloud_done_outlined, size: 48),
                SizedBox(height: 12),
                Text(
                  'Nenhum evento local aguardando sincronização.',
                  textAlign: TextAlign.center,
                ),
              ],
            );
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Text(
                'Retries reutilizam os mesmos UUIDs. Manifestos precisam ser aceitos antes do envio dos bytes.',
              ),
              if (widget.controller.errorMessage case final message?) ...[
                const SizedBox(height: 12),
                MaterialBanner(
                  content: Text(message),
                  actions: [
                    TextButton(
                      onPressed: _reload,
                      child: const Text('Recarregar'),
                    ),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              for (final item in values)
                _SyncItemCard(
                  item: item,
                  sending: runningKey == item.key,
                  onRetry: item.canRetry && runningKey == null
                      ? () => _retry(item)
                      : null,
                ),
              const SizedBox(height: 12),
              const Text(
                'Dados preparados e simulados continuam inelegíveis para execução, treinamento e relatório oficial.',
              ),
            ],
          );
        },
      ),
    ),
  );
}

class _SyncItemCard extends StatelessWidget {
  const _SyncItemCard({
    required this.item,
    required this.sending,
    required this.onRetry,
  });

  final SyncCenterItem item;
  final bool sending;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final status = sending ? SyncCenterStatus.sending : item.status;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(_statusIcon(status)),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    item.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Text(_statusLabel(status)),
              ],
            ),
            const SizedBox(height: 8),
            Text(item.subtitle),
            const SizedBox(height: 8),
            Text(
              item.attemptCount == 0
                  ? 'Nenhuma tentativa registrada.'
                  : '${item.attemptCount} tentativa(s) · última em ${item.lastAttemptAt!.toLocal().toIso8601String()}',
            ),
            if (status == SyncCenterStatus.rejected ||
                status == SyncCenterStatus.conflict) ...[
              const SizedBox(height: 6),
              const Text(
                'O resultado foi preservado. Revise a ordem; esta versão não sobrescreve eventos persistidos.',
              ),
            ],
            if (onRetry != null || sending) ...[
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: onRetry,
                icon: sending
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.sync),
                label: Text(sending ? 'Enviando…' : 'Tentar novamente'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

String _statusLabel(SyncCenterStatus status) => switch (status) {
  SyncCenterStatus.pending => 'Pendente',
  SyncCenterStatus.sending => 'Enviando',
  SyncCenterStatus.accepted => 'Aceito',
  SyncCenterStatus.rejected => 'Rejeitado',
  SyncCenterStatus.conflict => 'Conflito',
};

IconData _statusIcon(SyncCenterStatus status) => switch (status) {
  SyncCenterStatus.pending => Icons.schedule,
  SyncCenterStatus.sending => Icons.sync,
  SyncCenterStatus.accepted => Icons.cloud_done,
  SyncCenterStatus.rejected => Icons.cloud_off,
  SyncCenterStatus.conflict => Icons.warning_amber,
};
