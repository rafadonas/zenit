import 'package:flutter/material.dart';

import '../../../app/app_navigator.dart';
import '../../../app_controller.dart';

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
          Text(
            'Inspeções preparadas',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          if (controller.orders.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text('Nenhuma inspeção preparada disponível.'),
              ),
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
                onTap: () => AppNavigator.openInspectionDraft(
                  context,
                  controller: controller,
                  order: order,
                ),
              ),
            ),
          const SizedBox(height: 24),
          Text(
            'Planejamentos de roçada — demonstração',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          const Text(
            'Consulta offline com ensaio explicitamente simulado; nenhum controle autoriza execução real.',
          ),
          const SizedBox(height: 8),
          if (controller.mowingPlans.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Center(
                child: Text('Nenhum planejamento preparado disponível.'),
              ),
            ),
          for (final plan in controller.mowingPlans)
            Card(
              child: ListTile(
                leading: const CircleAvatar(child: Icon(Icons.grass)),
                title: Text('${plan.roadCode} · segmento ${plan.segmentIndex}'),
                subtitle: Text(
                  'Zona ${plan.zoneType} · preparado · NÃO EXECUTÁVEL',
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => AppNavigator.openMowingPlan(
                  context,
                  controller: controller,
                  plan: plan,
                ),
              ),
            ),
        ],
      ),
    ),
  );
}
