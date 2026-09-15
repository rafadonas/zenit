import 'package:flutter/material.dart';

import 'field_tokens.dart';

enum FieldBannerTone { info, warning, critical, success }

/// Field banner for operational, non-operational, or safety warnings.
/// Enforces WCAG accessibility: NEVER uses color as the sole indicator;
/// always includes an explicit icon, textual category tag, and Semantics.
class FieldBanner extends StatelessWidget {
  const FieldBanner({
    super.key,
    required this.message,
    this.title,
    this.tone = FieldBannerTone.info,
    this.icon,
    this.action,
  });

  const FieldBanner.critical({
    super.key,
    required this.message,
    this.title = 'NÃO AUTORIZA TRABALHO DE CAMPO',
    this.icon = Icons.block,
    this.action,
  }) : tone = FieldBannerTone.critical;

  const FieldBanner.warning({
    super.key,
    required this.message,
    this.title = 'ATENÇÃO',
    this.icon = Icons.warning_amber_rounded,
    this.action,
  }) : tone = FieldBannerTone.warning;

  const FieldBanner.info({
    super.key,
    required this.message,
    this.title = 'INFORMAÇÃO',
    this.icon = Icons.info_outline,
    this.action,
  }) : tone = FieldBannerTone.info;

  const FieldBanner.success({
    super.key,
    required this.message,
    this.title = 'CONCLUÍDO',
    this.icon = Icons.check_circle_outline,
    this.action,
  }) : tone = FieldBannerTone.success;

  final String message;
  final String? title;
  final FieldBannerTone tone;
  final IconData? icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final (
      Color bg,
      Color border,
      Color textCol,
      IconData defaultIcon,
      String defaultCategory,
    ) = switch (tone) {
      FieldBannerTone.critical => (
        FieldTokens.statusCriticalSurface,
        FieldTokens.statusCriticalBorder,
        FieldTokens.statusCriticalText,
        Icons.block,
        'NÃO AUTORIZAÇÃO / CRÍTICO',
      ),
      FieldBannerTone.warning => (
        FieldTokens.statusAttentionSurface,
        FieldTokens.statusAttentionBorder,
        FieldTokens.statusAttentionText,
        Icons.warning_amber_rounded,
        'ALERTA OPERACIONAL',
      ),
      FieldBannerTone.info => (
        FieldTokens.canvas,
        FieldTokens.borderStrong,
        FieldTokens.text,
        Icons.info_outline,
        'INFORMAÇÃO',
      ),
      FieldBannerTone.success => (
        FieldTokens.statusNormalSurface,
        FieldTokens.statusNormalBorder,
        FieldTokens.statusNormalText,
        Icons.check_circle_outline,
        'SUCESSO',
      ),
    };

    final effectiveIcon = icon ?? defaultIcon;
    final displayTitle = title ?? defaultCategory;

    return Semantics(
      container: true,
      liveRegion: tone == FieldBannerTone.critical,
      label: '$displayTitle: $message',
      child: Container(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(FieldTokens.radiusCard),
          border: Border.all(color: border, width: 1.5),
        ),
        padding: const EdgeInsets.all(FieldTokens.space4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Icon(effectiveIcon, color: textCol, size: 24),
                const SizedBox(width: FieldTokens.space2),
                Expanded(
                  child: Text(
                    displayTitle,
                    style: TextStyle(
                      color: textCol,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: FieldTokens.space2),
            Text(
              message,
              style: TextStyle(color: textCol, fontSize: 13, height: 1.4),
            ),
            if (action != null) ...[
              const SizedBox(height: FieldTokens.space3),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
