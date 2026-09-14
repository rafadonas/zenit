import 'package:flutter/material.dart';

import 'field_tokens.dart';

/// Field text field tailored for outdoor usage:
/// Enforces WCAG 44px minimum touch target, high sunlight border contrast,
/// clear label typography, and explicit multi-modal error presentation.
class FieldTextField extends StatelessWidget {
  const FieldTextField({
    super.key,
    required this.controller,
    required this.labelText,
    this.helperText,
    this.errorText,
    this.keyboardType,
    this.readOnly = false,
    this.enabled = true,
    this.obscureText = false,
    this.autofillHints,
    this.prefixIcon,
    this.suffix,
    this.onChanged,
  });

  final TextEditingController controller;
  final String labelText;
  final String? helperText;
  final String? errorText;
  final TextInputType? keyboardType;
  final bool readOnly;
  final bool enabled;
  final bool obscureText;
  final Iterable<String>? autofillHints;
  final IconData? prefixIcon;
  final Widget? suffix;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) {
    final hasError = errorText != null && errorText!.isNotEmpty;

    return Semantics(
      textField: true,
      label: labelText,
      value: controller.text,
      hint: helperText,
      readOnly: readOnly,
      enabled: enabled,
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          minHeight: FieldTokens.minTouchTarget,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: controller,
              keyboardType: keyboardType,
              readOnly: readOnly,
              enabled: enabled,
              obscureText: obscureText,
              autofillHints: autofillHints,
              onChanged: onChanged,
              style: const TextStyle(
                color: FieldTokens.text,
                fontSize: 15,
                fontWeight: FontWeight.w500,
              ),
              decoration: InputDecoration(
                labelText: labelText,
                helperText: helperText,
                errorText: null, // Error rendered explicitly below
                prefixIcon: prefixIcon != null ? Icon(prefixIcon) : null,
                suffix: suffix,
                filled: true,
                fillColor: enabled && !readOnly
                    ? FieldTokens.surface
                    : FieldTokens.canvas,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(
                    FieldTokens.radiusControl,
                  ),
                  borderSide: const BorderSide(
                    color: FieldTokens.borderStrong,
                    width: 1.2,
                  ),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(
                    FieldTokens.radiusControl,
                  ),
                  borderSide: BorderSide(
                    color: hasError
                        ? FieldTokens.statusCritical
                        : FieldTokens.borderStrong,
                    width: hasError ? 1.5 : 1.2,
                  ),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(
                    FieldTokens.radiusControl,
                  ),
                  borderSide: BorderSide(
                    color: hasError
                        ? FieldTokens.statusCritical
                        : FieldTokens.brand600,
                    width: 2.0,
                  ),
                ),
              ),
            ),
            if (hasError) ...[
              const SizedBox(height: FieldTokens.space1),
              Row(
                children: [
                  const Icon(
                    Icons.error_outline,
                    size: 16,
                    color: FieldTokens.statusCriticalText,
                  ),
                  const SizedBox(width: FieldTokens.space1),
                  Expanded(
                    child: Text(
                      errorText!,
                      style: const TextStyle(
                        color: FieldTokens.statusCriticalText,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
