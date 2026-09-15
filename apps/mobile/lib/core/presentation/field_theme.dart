import 'package:flutter/material.dart';

import 'field_tokens.dart';

/// Provides theme configuration for field mobile use, respecting WCAG 44px minimum
/// touch targets, outdoor sunlight contrast, and system typography scaling.
abstract final class FieldTheme {
  static ThemeData createTheme() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: FieldTokens.brand600,
      primary: FieldTokens.brand600,
      onPrimary: Colors.white,
      primaryContainer: FieldTokens.brand100,
      onPrimaryContainer: FieldTokens.brand800,
      surface: FieldTokens.surface,
      onSurface: FieldTokens.text,
      error: FieldTokens.statusCritical,
      onError: Colors.white,
      errorContainer: FieldTokens.statusCriticalSurface,
      onErrorContainer: FieldTokens.statusCriticalText,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: FieldTokens.canvas,
      cardTheme: CardThemeData(
        color: FieldTokens.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(FieldTokens.radiusCard),
          side: const BorderSide(color: FieldTokens.border, width: 1),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(
            FieldTokens.minTouchTarget,
            FieldTokens.minTouchTarget,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(
            FieldTokens.minTouchTarget,
            FieldTokens.minTouchTarget,
          ),
          side: const BorderSide(color: FieldTokens.borderStrong, width: 1.2),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: FieldTokens.surface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
          borderSide: const BorderSide(color: FieldTokens.border, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
          borderSide: const BorderSide(
            color: FieldTokens.borderStrong,
            width: 1.2,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
          borderSide: const BorderSide(color: FieldTokens.brand600, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(FieldTokens.radiusControl),
          borderSide: const BorderSide(
            color: FieldTokens.statusCritical,
            width: 1.5,
          ),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: FieldTokens.space4,
          vertical: FieldTokens.space3,
        ),
      ),
    );
  }
}
