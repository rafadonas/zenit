import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zenit_mobile/core/presentation/field_banner.dart';
import 'package:zenit_mobile/core/presentation/field_button.dart';
import 'package:zenit_mobile/core/presentation/field_card.dart';
import 'package:zenit_mobile/core/presentation/field_offline_indicator.dart';
import 'package:zenit_mobile/core/presentation/field_status_badge.dart';
import 'package:zenit_mobile/core/presentation/field_stepper.dart';
import 'package:zenit_mobile/core/presentation/field_text_field.dart';
import 'package:zenit_mobile/core/presentation/field_tokens.dart';
import 'package:zenit_mobile/domain/measurement_draft.dart';
import 'package:zenit_mobile/domain/sync_center.dart';

Widget _wrap(Widget child, {TextScaler? textScaler}) => MaterialApp(
  home: Scaffold(
    body: MediaQuery(
      data: MediaQueryData(
        textScaler: textScaler ?? TextScaler.noScaling,
        size: const Size(800, 1200),
      ),
      child: Center(child: child),
    ),
  ),
);

void main() {
  group('FieldTokens', () {
    test('aligns with WEB-001 design system tokens', () {
      expect(FieldTokens.brand600, const Color(0xFF5A26FF));
      expect(FieldTokens.brand800, const Color(0xFF35129A));
      expect(FieldTokens.brand100, const Color(0xFFEEE9FF));
      expect(FieldTokens.canvas, const Color(0xFFF7F7FA));
      expect(FieldTokens.surface, const Color(0xFFFFFFFF));
      expect(FieldTokens.text, const Color(0xFF202024));
      expect(FieldTokens.statusNormal, const Color(0xFF148A45));
      expect(FieldTokens.statusAttention, const Color(0xFFD8A900));
      expect(FieldTokens.statusNearLimit, const Color(0xFFF06A32));
      expect(FieldTokens.statusCritical, const Color(0xFFD82C55));
      expect(FieldTokens.statusUnknown, const Color(0xFF68686F));
      expect(FieldTokens.heightN1, const Color(0xFF35A566));
      expect(FieldTokens.heightN2, const Color(0xFFF1B82D));
      expect(FieldTokens.heightN3, const Color(0xFFE45745));
    });

    test('enforces WCAG minimum 44px touch target', () {
      expect(FieldTokens.minTouchTarget, 44.0);
    });

    test('defines geometric scale and radii', () {
      expect(FieldTokens.space1, 4.0);
      expect(FieldTokens.space2, 8.0);
      expect(FieldTokens.space3, 12.0);
      expect(FieldTokens.space4, 16.0);
      expect(FieldTokens.radiusControl, 8.0);
      expect(FieldTokens.radiusCard, 12.0);
      expect(FieldTokens.radiusPanel, 16.0);
      expect(FieldTokens.radiusPill, 999.0);
    });
  });

  group('FieldButton', () {
    testWidgets('enforces at least 44px height and handles clicks', (
      tester,
    ) async {
      var tapped = false;
      await tester.pumpWidget(
        _wrap(
          FieldButton(
            onPressed: () => tapped = true,
            label: 'Salvar rascunho',
            icon: Icons.save,
          ),
        ),
      );

      final renderBox = tester.renderObject<RenderBox>(
        find.byType(FieldButton),
      );
      expect(renderBox.size.height, greaterThanOrEqualTo(44.0));
      expect(renderBox.size.width, greaterThanOrEqualTo(44.0));

      await tester.tap(find.byType(FieldButton));
      expect(tapped, isTrue);
    });

    testWidgets('provides accessible semantics and loading state', (
      tester,
    ) async {
      await tester.pumpWidget(
        _wrap(
          const FieldButton(
            onPressed: null,
            label: 'Enviar dados',
            loading: true,
            semanticLabel: 'Sincronizando lote com o servidor',
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(
        tester.getSemantics(find.byType(FieldButton)),
        matchesSemantics(
          label: 'Sincronizando lote com o servidor',
          isButton: true,
          hasEnabledState: true,
          isEnabled: false,
        ),
      );
    });

    testWidgets('FieldIconButton enforces 44x44 minimum touch target', (
      tester,
    ) async {
      await tester.pumpWidget(
        _wrap(
          FieldIconButton(
            onPressed: () {},
            icon: Icons.refresh,
            tooltip: 'Atualizar ordens',
          ),
        ),
      );

      final renderBox = tester.renderObject<RenderBox>(
        find.byType(FieldIconButton),
      );
      expect(renderBox.size.height, greaterThanOrEqualTo(44.0));
      expect(renderBox.size.width, greaterThanOrEqualTo(44.0));
    });
  });

  group('FieldCard', () {
    testWidgets(
      'renders high outdoor contrast border and accessible container',
      (tester) async {
        await tester.pumpWidget(
          _wrap(
            const FieldCard(
              semanticLabel: 'Ordem de inspeção BR-101',
              child: Text('Card de teste'),
            ),
          ),
        );

        expect(find.text('Card de teste'), findsOneWidget);
        expect(
          tester.getSemantics(find.byType(FieldCard)).label,
          contains('Ordem de inspeção BR-101'),
        );
      },
    );
  });

  group('FieldBanner (no color-only indicator)', () {
    testWidgets(
      'every tone includes both an explicit icon and category title',
      (tester) async {
        await tester.pumpWidget(
          _wrap(
            const Column(
              children: [
                FieldBanner.critical(
                  message: 'Pontos não autorizam execução de campo.',
                ),
                FieldBanner.warning(message: 'Atenção aos limites do trecho.'),
                FieldBanner.info(message: 'Dados preparados localmente.'),
                FieldBanner.success(message: 'Lote confirmado no aparelho.'),
              ],
            ),
          ),
        );

        // Verify that critical banner has icon + text title
        expect(find.byIcon(Icons.block), findsOneWidget);
        expect(find.text('NÃO AUTORIZA TRABALHO DE CAMPO'), findsOneWidget);

        // Verify warning banner has icon + text title
        expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
        expect(find.text('ATENÇÃO'), findsOneWidget);

        // Verify info banner has icon + text title
        expect(find.byIcon(Icons.info_outline), findsOneWidget);
        expect(find.text('INFORMAÇÃO'), findsOneWidget);

        // Verify success banner has icon + text title
        expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
        expect(find.text('CONCLUÍDO'), findsOneWidget);
      },
    );
  });

  group('FieldStatusBadge (no color-only indicator)', () {
    testWidgets('combines icons and textual labels for all sync states', (
      tester,
    ) async {
      for (final state in DraftSyncState.values) {
        await tester.pumpWidget(_wrap(FieldStatusBadge.fromSyncState(state)));
        expect(find.byType(Icon), findsOneWidget);
        expect(find.byType(Text), findsOneWidget);
      }
    });

    testWidgets(
      'combines icons and textual labels for all sync center states',
      (tester) async {
        for (final status in SyncCenterStatus.values) {
          await tester.pumpWidget(
            _wrap(FieldStatusBadge.fromSyncCenterStatus(status)),
          );
          expect(find.byType(Icon), findsOneWidget);
          expect(find.byType(Text), findsOneWidget);
        }
      },
    );

    testWidgets(
      'combines icons and class tier text for vegetation height classes (N1, N2, N3)',
      (tester) async {
        // N1 < 10 cm
        await tester.pumpWidget(
          _wrap(FieldStatusBadge.fromVegetationHeight(6.0)),
        );
        expect(find.byIcon(Icons.grass), findsOneWidget);
        expect(find.text('N1 < 10 cm (6.0 cm)'), findsOneWidget);

        // N2 10-30 cm
        await tester.pumpWidget(
          _wrap(FieldStatusBadge.fromVegetationHeight(18.5)),
        );
        expect(find.byIcon(Icons.warning_amber), findsOneWidget);
        expect(find.text('N2 10-30 cm (18.5 cm)'), findsOneWidget);

        // N3 > 30 cm
        await tester.pumpWidget(
          _wrap(FieldStatusBadge.fromVegetationHeight(42.0)),
        );
        expect(find.byIcon(Icons.priority_high), findsOneWidget);
        expect(find.text('N3 > 30 cm (42.0 cm)'), findsOneWidget);
      },
    );
  });

  group('FieldTextField', () {
    testWidgets('enforces min 44px target and multimodal error feedback', (
      tester,
    ) async {
      final controller = TextEditingController(text: '12.5');
      await tester.pumpWidget(
        _wrap(
          FieldTextField(
            controller: controller,
            labelText: 'Altura do ponto 1 (cm)',
            helperText: 'Valor estimado',
            errorText: 'Valor fora dos limites aceitáveis',
          ),
        ),
      );

      final renderBox = tester.renderObject<RenderBox>(
        find.byType(FieldTextField),
      );
      expect(renderBox.size.height, greaterThanOrEqualTo(44.0));
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
      expect(find.text('Valor fora dos limites aceitáveis'), findsOneWidget);
    });
  });

  group('FieldStepper', () {
    testWidgets('renders numbers, icons, textual states, and semantics', (
      tester,
    ) async {
      var step2Tapped = false;
      await tester.pumpWidget(
        _wrap(
          FieldStepper(
            steps: [
              const FieldStepItem(
                stepNumber: 1,
                title: 'Confirmar',
                subtitle: 'Confirmado no aparelho',
                state: FieldStepState.complete,
              ),
              FieldStepItem(
                stepNumber: 2,
                title: 'Iniciar',
                subtitle: 'GPS simulado',
                state: FieldStepState.active,
                onTap: () => step2Tapped = true,
              ),
              const FieldStepItem(
                stepNumber: 3,
                title: 'Finalizar',
                subtitle: 'Aguardando medições',
                state: FieldStepState.disabled,
              ),
            ],
          ),
        ),
      );

      // Completed step has check icon
      expect(find.byIcon(Icons.check), findsOneWidget);
      // Active step has number '2' and state label 'Em andamento'
      expect(find.text('2'), findsOneWidget);
      expect(find.text('Em andamento'), findsOneWidget);
      // Disabled step has number '3' and state label 'Pendente'
      expect(find.text('3'), findsOneWidget);
      expect(find.text('Pendente'), findsOneWidget);

      await tester.tap(find.text('Iniciar'));
      expect(step2Tapped, isTrue);
    });
  });

  group('FieldOfflineIndicator', () {
    testWidgets('presents explicit lock icon and vault label', (tester) async {
      await tester.pumpWidget(_wrap(const FieldOfflineIndicator()));
      expect(find.byIcon(Icons.lock_outline), findsOneWidget);
      expect(find.text('Cofre criptografado no aparelho'), findsOneWidget);
    });
  });

  group('Font scaling resilience (escala de fonte)', () {
    testWidgets(
      'components scale gracefully at 2.0x text scale without errors',
      (tester) async {
        await tester.pumpWidget(
          _wrap(
            textScaler: const TextScaler.linear(2.0),
            SingleChildScrollView(
              child: Column(
                children: [
                  FieldButton(
                    onPressed: () {},
                    label: 'Botão com texto ampliado',
                  ),
                  const SizedBox(height: 8),
                  const FieldBanner.warning(
                    message: 'Texto de alerta com escala de fonte duplicada.',
                  ),
                  const SizedBox(height: 8),
                  FieldStatusBadge.fromVegetationHeight(25.0),
                  const SizedBox(height: 8),
                  FieldTextField(
                    controller: TextEditingController(text: '30.0'),
                    labelText: 'Altura (cm)',
                  ),
                ],
              ),
            ),
          ),
        );

        expect(tester.takeException(), isNull);
        expect(find.text('Botão com texto ampliado'), findsOneWidget);
        expect(find.text('N2 10-30 cm (25.0 cm)'), findsOneWidget);
      },
    );
  });
}
