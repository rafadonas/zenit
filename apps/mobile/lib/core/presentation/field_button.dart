import 'package:flutter/material.dart';

import 'field_tokens.dart';

enum FieldButtonVariant { filled, outlined, text, danger }

/// Field-ready accessible button that guarantees a minimum 44px touch target,
/// high outdoor sunlight contrast, clear loading state, and accessible semantics.
class FieldButton extends StatelessWidget {
  const FieldButton({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
    this.variant = FieldButtonVariant.filled,
    this.loading = false,
    this.semanticLabel,
    this.isFullWidth = false,
  });

  const FieldButton.filled({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
    this.loading = false,
    this.semanticLabel,
    this.isFullWidth = false,
  }) : variant = FieldButtonVariant.filled;

  const FieldButton.outlined({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
    this.loading = false,
    this.semanticLabel,
    this.isFullWidth = false,
  }) : variant = FieldButtonVariant.outlined;

  const FieldButton.danger({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
    this.loading = false,
    this.semanticLabel,
    this.isFullWidth = false,
  }) : variant = FieldButtonVariant.danger;

  final VoidCallback? onPressed;
  final String label;
  final IconData? icon;
  final FieldButtonVariant variant;
  final bool loading;
  final String? semanticLabel;
  final bool isFullWidth;

  @override
  Widget build(BuildContext context) {
    final effectiveOnPressed = loading ? null : onPressed;

    Widget buttonWidget;
    switch (variant) {
      case FieldButtonVariant.filled:
        if (loading) {
          buttonWidget = FilledButton(
            onPressed: null,
            child: _buildSpinner(Colors.white),
          );
        } else if (icon != null) {
          buttonWidget = FilledButton.icon(
            onPressed: effectiveOnPressed,
            icon: Icon(icon, size: 20),
            label: Text(label),
          );
        } else {
          buttonWidget = FilledButton(
            onPressed: effectiveOnPressed,
            child: Text(label),
          );
        }
        break;

      case FieldButtonVariant.outlined:
        if (loading) {
          buttonWidget = OutlinedButton(
            onPressed: null,
            child: _buildSpinner(FieldTokens.brand600),
          );
        } else if (icon != null) {
          buttonWidget = OutlinedButton.icon(
            onPressed: effectiveOnPressed,
            icon: Icon(icon, size: 20),
            label: Text(label),
          );
        } else {
          buttonWidget = OutlinedButton(
            onPressed: effectiveOnPressed,
            child: Text(label),
          );
        }
        break;

      case FieldButtonVariant.text:
        if (loading) {
          buttonWidget = TextButton(
            onPressed: null,
            child: _buildSpinner(FieldTokens.brand600),
          );
        } else if (icon != null) {
          buttonWidget = TextButton.icon(
            onPressed: effectiveOnPressed,
            icon: Icon(icon, size: 20),
            label: Text(label),
          );
        } else {
          buttonWidget = TextButton(
            onPressed: effectiveOnPressed,
            child: Text(label),
          );
        }
        break;

      case FieldButtonVariant.danger:
        final style = FilledButton.styleFrom(
          backgroundColor: FieldTokens.statusCritical,
          foregroundColor: Colors.white,
        );
        if (loading) {
          buttonWidget = FilledButton(
            style: style,
            onPressed: null,
            child: _buildSpinner(Colors.white),
          );
        } else if (icon != null) {
          buttonWidget = FilledButton.icon(
            style: style,
            onPressed: effectiveOnPressed,
            icon: Icon(icon, size: 20),
            label: Text(label),
          );
        } else {
          buttonWidget = FilledButton(
            style: style,
            onPressed: effectiveOnPressed,
            child: Text(label),
          );
        }
        break;
    }

    return Semantics(
      button: true,
      enabled: effectiveOnPressed != null,
      label: semanticLabel ?? label,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          minHeight: FieldTokens.minTouchTarget,
          minWidth: isFullWidth ? double.infinity : FieldTokens.minTouchTarget,
        ),
        child: buttonWidget,
      ),
    );
  }

  Widget _buildSpinner(Color color) => SizedBox.square(
    dimension: 20,
    child: CircularProgressIndicator(strokeWidth: 2, color: color),
  );
}

/// Accessible icon button enforcing minimum 44x44px touch target.
class FieldIconButton extends StatelessWidget {
  const FieldIconButton({
    super.key,
    required this.onPressed,
    required this.icon,
    required this.tooltip,
  });

  final VoidCallback? onPressed;
  final IconData icon;
  final String tooltip;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    enabled: onPressed != null,
    label: tooltip,
    child: ConstrainedBox(
      constraints: const BoxConstraints(
        minWidth: FieldTokens.minTouchTarget,
        minHeight: FieldTokens.minTouchTarget,
      ),
      child: IconButton(
        onPressed: onPressed,
        tooltip: tooltip,
        icon: Icon(icon),
      ),
    ),
  );
}
