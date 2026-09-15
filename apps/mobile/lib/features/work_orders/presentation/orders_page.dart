import 'package:flutter/material.dart';

import '../../../app/app_navigator.dart';
import '../../../app_controller.dart';
import '../../../core/presentation/field_banner.dart';
import '../../../core/presentation/field_card.dart';
import '../../../core/presentation/field_offline_indicator.dart';
import '../../../core/presentation/field_tokens.dart';

class OrdersPage extends StatelessWidget {
  const OrdersPage({super.key, required this.controller});

  final ZenitAppController controller;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Ordens preparadas'),
      actions: [
        IconButton(
          onPressed: () =>
              AppNavigator.openSyncCenter(context, controller: controller),
          tooltip: 'Abrir central de sincronização',
          icon: const Icon(Icons.cloud_sync),
        ),
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
        padding: const EdgeInsets.all(FieldTokens.space4),
        children: [
          const FieldBanner.critical(
            title: 'NÃO AUTORIZA TRABALHO DE CAMPO',
            message:
                'Pontos e medições deste app são preparados, locais e inelegíveis para relatório oficial.',
          ),
          const SizedBox(height: FieldTokens.space3),
          const Row(
            children: [
              FieldOfflineIndicator(compact: true),
              SizedBox(width: FieldTokens.space2),
              Expanded(
                child: Text(
                  'Cofre ativo no aparelho · sincronização em primeiro plano',
                  style: TextStyle(fontSize: 12, color: FieldTokens.textMuted),
                ),
              ),
            ],
          ),
          if (controller.errorMessage case final message?) ...[
            const SizedBox(height: FieldTokens.space2),
            Text(
              message,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: FieldTokens.space4),
          Text(
            'Inspeções preparadas',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: FieldTokens.space2),
          if (controller.orders.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text('Nenhuma inspeção preparada disponível.'),
              ),
            ),
          for (final order in controller.orders)
            Padding(
              padding: const EdgeInsets.only(bottom: FieldTokens.space3),
              child: FieldCard(
                onTap: () => AppNavigator.openInspectionDraft(
                  context,
                  controller: controller,
                  order: order,
                ),
                semanticLabel:
                    'Ordem de inspeção ${order.roadCode} segmento ${order.segmentIndex}',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    backgroundColor: FieldTokens.brand100,
                    foregroundColor: FieldTokens.brand800,
                    child: const Icon(Icons.route),
                  ),
                  title: Text(
                    '${order.roadCode} · segmento ${order.segmentIndex}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    'Zona ${order.zoneType} · 3 pontos · somente rascunho local',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                ),
              ),
            ),
          const SizedBox(height: FieldTokens.space4),
          Text(
            'Planejamentos de roçada — demonstração',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: FieldTokens.space2),
          const Text(
            'Consulta offline com ensaio explicitamente simulado; nenhum controle autoriza execução real.',
          ),
          const SizedBox(height: FieldTokens.space2),
          if (controller.mowingPlans.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text('Nenhum planejamento preparado disponível.'),
              ),
            ),
          for (final plan in controller.mowingPlans)
            Padding(
              padding: const EdgeInsets.only(bottom: FieldTokens.space3),
              child: FieldCard(
                onTap: () => AppNavigator.openMowingPlan(
                  context,
                  controller: controller,
                  plan: plan,
                ),
                semanticLabel:
                    'Planejamento de roçada simulado ${plan.roadCode} segmento ${plan.segmentIndex}',
                child: ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    backgroundColor: FieldTokens.statusNearLimitSurface,
                    foregroundColor: FieldTokens.statusNearLimitText,
                    child: const Icon(Icons.grass),
                  ),
                  title: Text(
                    '${plan.roadCode} · segmento ${plan.segmentIndex}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    'Zona ${plan.zoneType} · preparado · NÃO EXECUTÁVEL',
                  ),
                  trailing: const Icon(Icons.chevron_right),
                ),
              ),
            ),
        ],
      ),
    ),
  );
}
