import 'package:flutter/material.dart';

import '../../domain/measurement_draft.dart';
import '../../domain/sync_center.dart';
import 'field_tokens.dart';

enum FieldStatusTone { normal, attention, nearLimit, critical, unknown }

/// Accessible status badge for field sync states, operational tiers, and vegetation heights.
/// Adheres strictly to the requirement: NEVER use color as the sole indicator;
/// every badge combines an explicit Icon with a Textual label and Semantics.
class FieldStatusBadge extends StatelessWidget {
  const FieldStatusBadge({
    super.key,
    required this.label,
    required this.icon,
    this.tone = FieldStatusTone.unknown,
    this.semanticLabel,
    this.dense = false,
  });

  factory FieldStatusBadge.fromSyncState(DraftSyncState state) {
    return switch (state) {
      DraftSyncState.localOnly => const FieldStatusBadge(
        label: 'Somente local',
        icon: Icons.phone_android,
        tone: FieldStatusTone.unknown,
      ),
      DraftSyncState.pending => const FieldStatusBadge(
        label: 'Aguardando confirmação',
        icon: Icons.sync,
        tone: FieldStatusTone.attention,
      ),
      DraftSyncState.acknowledged => const FieldStatusBadge(
        label: 'Persistido no servidor',
        icon: Icons.cloud_done,
        tone: FieldStatusTone.normal,
      ),
      DraftSyncState.rejected => const FieldStatusBadge(
        label: 'Rejeitado pelo servidor',
        icon: Icons.cloud_off,
        tone: FieldStatusTone.critical,
      ),
      DraftSyncState.conflict => const FieldStatusBadge(
        label: 'Conflito preservado',
        icon: Icons.warning_amber,
        tone: FieldStatusTone.nearLimit,
      ),
    };
  }

  factory FieldStatusBadge.fromSyncCenterStatus(SyncCenterStatus status) {
    return switch (status) {
      SyncCenterStatus.pending => const FieldStatusBadge(
        label: 'Pendente',
        icon: Icons.schedule,
        tone: FieldStatusTone.attention,
      ),
      SyncCenterStatus.sending => const FieldStatusBadge(
        label: 'Enviando…',
        icon: Icons.sync,
        tone: FieldStatusTone.unknown,
      ),
      SyncCenterStatus.accepted => const FieldStatusBadge(
        label: 'Aceito',
        icon: Icons.cloud_done,
        tone: FieldStatusTone.normal,
      ),
      SyncCenterStatus.rejected => const FieldStatusBadge(
        label: 'Rejeitado',
        icon: Icons.cloud_off,
        tone: FieldStatusTone.critical,
      ),
      SyncCenterStatus.conflict => const FieldStatusBadge(
        label: 'Conflito',
        icon: Icons.warning_amber,
        tone: FieldStatusTone.nearLimit,
      ),
    };
  }

  factory FieldStatusBadge.fromVegetationHeight(double heightCm) {
    if (heightCm < 10.0) {
      return FieldStatusBadge(
        label: 'N1 < 10 cm (${heightCm.toStringAsFixed(1)} cm)',
        icon: Icons.grass,
        tone: FieldStatusTone.normal,
      );
    } else if (heightCm <= 30.0) {
      return FieldStatusBadge(
        label: 'N2 10-30 cm (${heightCm.toStringAsFixed(1)} cm)',
        icon: Icons.warning_amber,
        tone: FieldStatusTone.attention,
      );
    } else {
      return FieldStatusBadge(
        label: 'N3 > 30 cm (${heightCm.toStringAsFixed(1)} cm)',
        icon: Icons.priority_high,
        tone: FieldStatusTone.critical,
      );
    }
  }

  final String label;
  final IconData icon;
  final FieldStatusTone tone;
  final String? semanticLabel;
  final bool dense;

  @override
  Widget build(BuildContext context) {
    final (Color bg, Color border, Color textCol) = switch (tone) {
      FieldStatusTone.normal => (
        FieldTokens.statusNormalSurface,
        FieldTokens.statusNormalBorder,
        FieldTokens.statusNormalText,
      ),
      FieldStatusTone.attention => (
        FieldTokens.statusAttentionSurface,
        FieldTokens.statusAttentionBorder,
        FieldTokens.statusAttentionText,
      ),
      FieldStatusTone.nearLimit => (
        FieldTokens.statusNearLimitSurface,
        FieldTokens.statusNearLimitBorder,
        FieldTokens.statusNearLimitText,
      ),
      FieldStatusTone.critical => (
        FieldTokens.statusCriticalSurface,
        FieldTokens.statusCriticalBorder,
        FieldTokens.statusCriticalText,
      ),
      FieldStatusTone.unknown => (
        FieldTokens.statusUnknownSurface,
        FieldTokens.statusUnknownBorder,
        FieldTokens.statusUnknownText,
      ),
    };

    return Semantics(
      label: semanticLabel ?? 'Status: $label',
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: dense ? FieldTokens.space2 : FieldTokens.space3,
          vertical: dense ? FieldTokens.space1 : FieldTokens.space2,
        ),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(FieldTokens.radiusPill),
          border: Border.all(color: border, width: 1.2),
        ),
        child: Wrap(
          spacing: dense ? 4 : 6,
          runSpacing: FieldTokens.space1,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Icon(icon, size: dense ? 14 : 16, color: textCol),
            Text(
              label,
              style: TextStyle(
                color: textCol,
                fontWeight: FontWeight.w600,
                fontSize: dense ? 11 : 13,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
