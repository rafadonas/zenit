import 'package:flutter/material.dart';

import 'field_tokens.dart';

/// Indicates that the mobile client operates in offline, locally encrypted vault mode.
/// Reinforces that drafts, measurements, and photos are safely stored on device.
class FieldOfflineIndicator extends StatelessWidget {
  const FieldOfflineIndicator({super.key, this.compact = false});

  final bool compact;

  @override
  Widget build(BuildContext context) => Semantics(
    label:
        'Modo local ativo: dados e rascunhos são armazenados no cofre criptografado do aparelho',
    child: Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? FieldTokens.space2 : FieldTokens.space3,
        vertical: compact ? FieldTokens.space1 : FieldTokens.space2,
      ),
      decoration: BoxDecoration(
        color: FieldTokens.surface,
        borderRadius: BorderRadius.circular(FieldTokens.radiusPill),
        border: Border.all(color: FieldTokens.borderStrong, width: 1.2),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.lock_outline, size: 16, color: FieldTokens.brand600),
          const SizedBox(width: FieldTokens.space1),
          Text(
            compact ? 'Local seguro' : 'Cofre criptografado no aparelho',
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: FieldTokens.text,
            ),
          ),
        ],
      ),
    ),
  );
}
