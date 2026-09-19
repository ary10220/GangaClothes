import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/theme.dart';
import 'package:mobile/shared/widgets/gc_app_bar.dart';
import 'package:mobile/shared/widgets/gc_button.dart';
import 'package:mobile/shared/widgets/gc_chip.dart';
import 'package:mobile/shared/widgets/gc_feedback.dart';
import 'package:mobile/shared/widgets/gc_field.dart';
import 'package:mobile/shared/widgets/gc_loading_empty_error.dart';
import 'package:mobile/shared/widgets/gc_status_badge.dart';

Widget _host(Widget child) => MaterialApp(
  theme: gangaTheme(),
  home: Scaffold(body: child),
);

void main() {
  test('exposes the extracted color tokens and Material 3 theme', () {
    final theme = gangaTheme();

    expect(GangaColors.paper, const Color(0xFFF2F2ED));
    expect(GangaColors.brand, const Color(0xFFE8175D));
    expect(GangaColors.lightError, const Color(0xFFFCE9E2));
    expect(theme.useMaterial3, isTrue);
    expect(theme.scaffoldBackgroundColor, GangaColors.paper);
    expect(theme.colorScheme.primary, GangaColors.brand);
    expect(theme.inputDecorationTheme.border, isA<OutlineInputBorder>());
  });

  testWidgets('renders every button variant and loading state', (tester) async {
    await tester.pumpWidget(
      _host(
        const Wrap(
          children: [
            GcButton(label: 'Primary', onPressed: _noop),
            GcButton(
              label: 'Secondary',
              variant: GcButtonVariant.secondary,
              onPressed: _noop,
            ),
            GcButton(
              label: 'Outlined',
              variant: GcButtonVariant.outlined,
              onPressed: _noop,
            ),
            GcButton(
              label: 'Danger',
              variant: GcButtonVariant.danger,
              onPressed: _noop,
            ),
            GcButton(label: 'Loading', loading: true, onPressed: _noop),
          ],
        ),
      ),
    );

    expect(find.text('Primary'), findsOneWidget);
    expect(find.text('Secondary'), findsOneWidget);
    expect(find.text('Outlined'), findsOneWidget);
    expect(find.text('Danger'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(
      tester.getSize(find.bySemanticsLabel('Primary')).height,
      greaterThanOrEqualTo(48),
    );
  });

  testWidgets('renders field label, hint, and error', (tester) async {
    await tester.pumpWidget(
      _host(
        const Padding(
          padding: EdgeInsets.all(16),
          child: GcField(
            label: 'Email',
            hint: 'Email address',
            errorText: 'Required',
          ),
        ),
      ),
    );

    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Email address'), findsOneWidget);
    expect(find.text('Required'), findsOneWidget);
  });

  testWidgets('chip exposes selection and responds to a tap', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      _host(GcChip(label: 'Season', selected: true, onTap: () => taps++)),
    );

    expect(find.text('Season'), findsOneWidget);
    expect(
      tester.getSize(find.bySemanticsLabel('Season')).height,
      greaterThanOrEqualTo(44),
    );
    await tester.tap(find.text('Season'));
    expect(taps, 1);
  });

  testWidgets('renders all status badge variants', (tester) async {
    await tester.pumpWidget(
      _host(
        const Wrap(
          children: [
            GcStatusBadge(
              text: 'Success',
              variant: GcStatusBadgeVariant.success,
            ),
            GcStatusBadge(text: 'Error', variant: GcStatusBadgeVariant.error),
            GcStatusBadge(text: 'Brand', variant: GcStatusBadgeVariant.brand),
            GcStatusBadge(text: 'Neutral'),
          ],
        ),
      ),
    );

    expect(find.text('Success'), findsOneWidget);
    expect(find.text('Error'), findsOneWidget);
    expect(find.text('Brand'), findsOneWidget);
    expect(find.text('Neutral'), findsOneWidget);
  });

  testWidgets('renders feedback variants, action, and dismiss controls', (
    tester,
  ) async {
    var actionCount = 0;
    var dismissCount = 0;
    await tester.pumpWidget(
      _host(
        Column(
          children: [
            const GcFeedback(message: 'Neutral'),
            const GcFeedback(
              message: 'Success',
              variant: GcFeedbackVariant.success,
            ),
            GcFeedback(
              message: 'Error',
              variant: GcFeedbackVariant.error,
              actionLabel: 'Retry',
              onAction: () => actionCount++,
              onDismiss: () => dismissCount++,
            ),
          ],
        ),
      ),
    );

    expect(find.text('Neutral'), findsOneWidget);
    expect(find.text('Success'), findsOneWidget);
    expect(find.text('Error'), findsOneWidget);
    await tester.tap(find.text('Retry'));
    await tester.tap(find.byTooltip('Dismiss'));
    expect(actionCount, 1);
    expect(dismissCount, 1);
  });

  testWidgets('renders loading, empty, and retryable error panels', (
    tester,
  ) async {
    var retries = 0;
    await tester.pumpWidget(
      _host(
        Column(
          children: [
            const GcLoadingEmptyError(state: GcPanelState.loading),
            const GcLoadingEmptyError(
              state: GcPanelState.empty,
              emptyTitle: 'Empty',
            ),
            GcLoadingEmptyError(
              state: GcPanelState.error,
              errorTitle: 'Error panel',
              errorMessage: 'Try again',
              onRetry: () => retries++,
            ),
          ],
        ),
      ),
    );

    expect(find.text('Cargando…'), findsOneWidget);
    expect(find.text('Empty'), findsOneWidget);
    expect(find.text('Error panel'), findsOneWidget);
    await tester.tap(find.text('Retry'));
    expect(retries, 1);
  });

  testWidgets('app bar exposes destinations and account semantics', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        Scaffold(
          appBar: GcAppBar(
            destinations: [
              GcAppBarDestination(label: 'Catalog', onPressed: _noop),
            ],
            accountName: 'Ada',
            accountRole: 'customer',
            onAccountPressed: _noop,
          ),
        ),
      ),
    );

    expect(find.text('GangaClothes'), findsOneWidget);
    expect(find.text('Catalog'), findsOneWidget);
    expect(find.text('Ada · customer'), findsOneWidget);
    expect(find.bySemanticsLabel('Catalog'), findsOneWidget);
    expect(find.bySemanticsLabel('Ada, customer'), findsOneWidget);
  });

  testWidgets('narrow app bar scrolls destinations and account actions', (
    tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(320, 200));
    var accountTaps = 0;
    var logoutTaps = 0;

    await tester.pumpWidget(
      _host(
        Scaffold(
          appBar: GcAppBar(
            destinations: [
              GcAppBarDestination(label: 'Catalog', onPressed: _noop),
              GcAppBarDestination(label: 'Reservations', onPressed: _noop),
              GcAppBarDestination(label: 'Cart', onPressed: _noop),
            ],
            accountName: 'Ada',
            accountRole: 'customer',
            onAccountPressed: () => accountTaps++,
            onLogout: () => logoutTaps++,
          ),
        ),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
    final scrollable = tester.state<ScrollableState>(find.byType(Scrollable));
    expect(scrollable.position.maxScrollExtent, greaterThan(0));

    scrollable.position.jumpTo(scrollable.position.maxScrollExtent);
    await tester.pump();
    expect(tester.takeException(), isNull);
    expect(
      tester.getCenter(find.byTooltip('Log out')).dx,
      lessThanOrEqualTo(320),
    );
    expect(find.text('Ada · customer'), findsOneWidget);

    await tester.tap(find.byTooltip('Log out'));
    expect(logoutTaps, 1);
    expect(accountTaps, 0);
  });
}

void _noop() {}
