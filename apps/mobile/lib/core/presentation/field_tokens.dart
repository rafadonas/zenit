import 'package:flutter/material.dart';

/// Design tokens aligned with the ZENIT master design system (WEB-001/tokens.css)
/// optimized for field mobile usage under outdoor and bright sunlight conditions.
abstract final class FieldTokens {
  // Brand colors
  static const brand600 = Color(0xFF5A26FF);
  static const brand800 = Color(0xFF35129A);
  static const brand100 = Color(0xFFEEE9FF);

  // Surfaces, canvas and ink
  static const canvas = Color(0xFFF7F7FA);
  static const surface = Color(0xFFFFFFFF);
  static const text = Color(0xFF202024);
  static const textMuted = Color(0xFF68686F);
  static const border = Color(0xFFE4E3EC);

  /// High-contrast border specifically tuned for outdoor and direct sunlight visibility.
  static const borderStrong = Color(0xFF9E9EA7);

  // Semantic status colors
  static const statusNormal = Color(0xFF148A45);
  static const statusNormalSurface = Color(0xFFEAF8EF);
  static const statusNormalText = Color(0xFF156434);
  static const statusNormalBorder = Color(0xFFC5E6D1);

  static const statusAttention = Color(0xFFD8A900);
  static const statusAttentionSurface = Color(0xFFFFFDEB);
  static const statusAttentionText = Color(0xFF7A5F00);
  static const statusAttentionBorder = Color(0xFFF5E48C);

  static const statusNearLimit = Color(0xFFF06A32);
  static const statusNearLimitSurface = Color(0xFFFFF0E9);
  static const statusNearLimitText = Color(0xFF8B391F);
  static const statusNearLimitBorder = Color(0xFFFFD2C4);

  static const statusCritical = Color(0xFFD82C55);
  static const statusCriticalSurface = Color(0xFFFDF0F3);
  static const statusCriticalText = Color(0xFF8C132E);
  static const statusCriticalBorder = Color(0xFFF7BCC9);

  static const statusUnknown = Color(0xFF68686F);
  static const statusUnknownSurface = Color(0xFFF2F2F5);
  static const statusUnknownText = Color(0xFF3D3D42);
  static const statusUnknownBorder = Color(0xFFD1D1D8);

  // Historical vegetation height thresholds
  // N1: < 10 cm, N2: 10-30 cm, N3: > 30 cm
  static const heightN1 = Color(0xFF35A566);
  static const heightN2 = Color(0xFFF1B82D);
  static const heightN3 = Color(0xFFE45745);

  // Spacing
  static const double space1 = 4.0;
  static const double space2 = 8.0;
  static const double space3 = 12.0;
  static const double space4 = 16.0;
  static const double space6 = 24.0;
  static const double space8 = 32.0;
  static const double space10 = 40.0;
  static const double space12 = 48.0;

  // Radii
  static const double radiusControl = 8.0;
  static const double radiusCard = 12.0;
  static const double radiusPanel = 16.0;
  static const double radiusPill = 999.0;

  // Minimum touch target (WCAG 2.5.5 / 2.5.8 and field acceptance criteria)
  static const double minTouchTarget = 44.0;
}
