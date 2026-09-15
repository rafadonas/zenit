import 'package:flutter/material.dart';

import 'field_tokens.dart';

/// High-contrast field card designed for outdoor legibility and touch accessibility.
class FieldCard extends StatelessWidget {
  const FieldCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(FieldTokens.space4),
    this.onTap,
    this.borderColor,
    this.backgroundColor,
    this.semanticLabel,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;
  final Color? borderColor;
  final Color? backgroundColor;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final effectiveBorderColor = borderColor ?? FieldTokens.border;
    final effectiveBackgroundColor = backgroundColor ?? FieldTokens.surface;

    Widget content = Container(
      decoration: BoxDecoration(
        color: effectiveBackgroundColor,
        borderRadius: BorderRadius.circular(FieldTokens.radiusCard),
        border: Border.all(color: effectiveBorderColor, width: 1.2),
      ),
      child: Material(
        color: Colors.transparent,
        child: onTap != null
            ? InkWell(
                onTap: onTap,
                borderRadius: BorderRadius.circular(FieldTokens.radiusCard),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    minHeight: FieldTokens.minTouchTarget,
                  ),
                  child: Padding(
                    padding: padding ?? EdgeInsets.zero,
                    child: child,
                  ),
                ),
              )
            : Padding(padding: padding ?? EdgeInsets.zero, child: child),
      ),
    );

    if (semanticLabel != null) {
      content = Semantics(
        container: true,
        label: semanticLabel,
        button: onTap != null,
        child: content,
      );
    }

    return content;
  }
}
