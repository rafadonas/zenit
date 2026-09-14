import 'package:flutter/material.dart';

import 'field_tokens.dart';

enum FieldStepState { disabled, active, complete }

class FieldStepItem {
  const FieldStepItem({
    required this.stepNumber,
    required this.title,
    this.subtitle,
    required this.state,
    this.onTap,
  });

  final int stepNumber;
  final String title;
  final String? subtitle;
  final FieldStepState state;
  final VoidCallback? onTap;
}

/// Accessible field stepper designed for multi-step inspection and mowing rehearsal lifecycles.
/// Never relies on color alone: uses numbers, state icons (check marks, clocks), and accessible semantics.
class FieldStepper extends StatelessWidget {
  const FieldStepper({
    super.key,
    required this.steps,
    this.direction = Axis.vertical,
  });

  final List<FieldStepItem> steps;
  final Axis direction;

  @override
  Widget build(BuildContext context) {
    if (direction == Axis.horizontal) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          for (var i = 0; i < steps.length; i++) ...[
            Expanded(child: _buildHorizontalStep(context, steps[i])),
            if (i < steps.length - 1)
              Container(
                width: 20,
                height: 2,
                color: steps[i].state == FieldStepState.complete
                    ? FieldTokens.statusNormal
                    : FieldTokens.borderStrong,
              ),
          ],
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = 0; i < steps.length; i++) ...[
          _buildVerticalStep(context, steps[i]),
          if (i < steps.length - 1)
            Padding(
              padding: const EdgeInsets.only(left: 18),
              child: Container(
                width: 2,
                height: 16,
                color: steps[i].state == FieldStepState.complete
                    ? FieldTokens.statusNormal
                    : FieldTokens.borderStrong,
              ),
            ),
        ],
      ],
    );
  }

  Widget _buildHorizontalStep(BuildContext context, FieldStepItem step) {
    final statusLabel = switch (step.state) {
      FieldStepState.complete => 'Concluído',
      FieldStepState.active => 'Em andamento',
      FieldStepState.disabled => 'Pendente',
    };

    return Semantics(
      button: step.onTap != null,
      enabled: step.onTap != null,
      label: 'Passo ${step.stepNumber}: ${step.title} ($statusLabel)',
      child: InkWell(
        onTap: step.onTap,
        borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
        child: ConstrainedBox(
          constraints: const BoxConstraints(
            minHeight: FieldTokens.minTouchTarget,
          ),
          child: Padding(
            padding: const EdgeInsets.all(FieldTokens.space2),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildIndicator(step),
                const SizedBox(height: FieldTokens.space1),
                Text(
                  step.title,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: step.state == FieldStepState.active
                        ? FontWeight.bold
                        : FontWeight.normal,
                    color: step.state == FieldStepState.disabled
                        ? FieldTokens.textMuted
                        : FieldTokens.text,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildVerticalStep(BuildContext context, FieldStepItem step) {
    final statusLabel = switch (step.state) {
      FieldStepState.complete => 'Concluído',
      FieldStepState.active => 'Em andamento',
      FieldStepState.disabled => 'Pendente',
    };

    return Semantics(
      button: step.onTap != null,
      enabled: step.onTap != null,
      label: 'Passo ${step.stepNumber}: ${step.title} ($statusLabel)',
      child: InkWell(
        onTap: step.onTap,
        borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
        child: ConstrainedBox(
          constraints: const BoxConstraints(
            minHeight: FieldTokens.minTouchTarget,
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              vertical: FieldTokens.space1,
              horizontal: FieldTokens.space2,
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                _buildIndicator(step),
                const SizedBox(width: FieldTokens.space3),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        step.title,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: step.state == FieldStepState.active
                              ? FontWeight.bold
                              : FontWeight.w500,
                          color: step.state == FieldStepState.disabled
                              ? FieldTokens.textMuted
                              : FieldTokens.text,
                        ),
                      ),
                      if (step.subtitle != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          step.subtitle!,
                          style: const TextStyle(
                            fontSize: 12,
                            color: FieldTokens.textMuted,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                Text(
                  statusLabel,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: switch (step.state) {
                      FieldStepState.complete => FieldTokens.statusNormalText,
                      FieldStepState.active => FieldTokens.brand600,
                      FieldStepState.disabled => FieldTokens.textMuted,
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildIndicator(FieldStepItem step) {
    switch (step.state) {
      case FieldStepState.complete:
        return Container(
          width: 36,
          height: 36,
          decoration: const BoxDecoration(
            color: FieldTokens.statusNormal,
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.check, color: Colors.white, size: 20),
        );
      case FieldStepState.active:
        return Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: FieldTokens.brand100,
            shape: BoxShape.circle,
            border: Border.all(color: FieldTokens.brand600, width: 2),
          ),
          child: Center(
            child: Text(
              '${step.stepNumber}',
              style: const TextStyle(
                color: FieldTokens.brand800,
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
          ),
        );
      case FieldStepState.disabled:
        return Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: FieldTokens.surface,
            shape: BoxShape.circle,
            border: Border.all(color: FieldTokens.borderStrong, width: 1.5),
          ),
          child: Center(
            child: Text(
              '${step.stepNumber}',
              style: const TextStyle(
                color: FieldTokens.textMuted,
                fontWeight: FontWeight.w600,
                fontSize: 15,
              ),
            ),
          ),
        );
    }
  }
}
