import 'package:flutter/material.dart';

import '../../app/theme.dart';
import 'gc_button.dart';

enum GcPanelState { loading, empty, error }

class GcLoadingEmptyError extends StatelessWidget {
  const GcLoadingEmptyError({
    required this.state,
    this.emptyTitle = 'No hay contenido todavía',
    this.emptyMessage,
    this.errorTitle = 'No se pudo cargar',
    this.errorMessage = 'Intenta de nuevo.',
    this.onRetry,
    this.retryLabel = 'Retry',
    super.key,
  });

  final GcPanelState state;
  final String emptyTitle;
  final String? emptyMessage;
  final String errorTitle;
  final String errorMessage;
  final VoidCallback? onRetry;
  final String retryLabel;

  @override
  Widget build(BuildContext context) => switch (state) {
    GcPanelState.loading => const GcLoadingPanel(),
    GcPanelState.empty => GcEmptyPanel(
      title: emptyTitle,
      message: emptyMessage,
    ),
    GcPanelState.error => GcErrorPanel(
      title: errorTitle,
      message: errorMessage,
      onRetry: onRetry,
      retryLabel: retryLabel,
    ),
  };
}

class GcLoadingPanel extends StatelessWidget {
  const GcLoadingPanel({super.key});

  @override
  Widget build(BuildContext context) => Semantics(
    container: true,
    liveRegion: true,
    label: 'Cargando…',
    child: Padding(
      padding: EdgeInsets.symmetric(vertical: 26),
      child: Center(child: Text('Cargando…')),
    ),
  );
}

class GcEmptyPanel extends StatelessWidget {
  const GcEmptyPanel({required this.title, this.message, super.key});

  final String title;
  final String? message;

  @override
  Widget build(BuildContext context) => _DashedPanel(
    color: GangaColors.line,
    child: Semantics(
      container: true,
      label: [title, ?message].join('. '),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              textAlign: TextAlign.center,
              style: GangaTextStyles.subheading,
            ),
            if (message != null) ...[
              const SizedBox(height: 8),
              Text(
                message!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: GangaColors.gray, fontSize: 13),
              ),
            ],
          ],
        ),
      ),
    ),
  );
}

class GcErrorPanel extends StatelessWidget {
  const GcErrorPanel({
    required this.title,
    required this.message,
    this.onRetry,
    this.retryLabel = 'Retry',
    super.key,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;
  final String retryLabel;

  @override
  Widget build(BuildContext context) => _DashedPanel(
    color: GangaColors.alert,
    child: Semantics(
      container: true,
      liveRegion: true,
      label: '$title. $message',
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              textAlign: TextAlign.center,
              style: GangaTextStyles.subheading.copyWith(
                color: GangaColors.alert,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: GangaColors.alert, fontSize: 13),
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              GcButton(
                label: retryLabel,
                variant: GcButtonVariant.outlined,
                onPressed: onRetry,
                semanticLabel: retryLabel,
              ),
            ],
          ],
        ),
      ),
    ),
  );
}

class _DashedPanel extends StatelessWidget {
  const _DashedPanel({required this.color, required this.child});

  final Color color;
  final Widget child;

  @override
  Widget build(BuildContext context) => CustomPaint(
    painter: _DashedBorderPainter(color),
    child: Container(
      width: double.infinity,
      color: GangaColors.white,
      child: child,
    ),
  );
}

class _DashedBorderPainter extends CustomPainter {
  const _DashedBorderPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    final path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(13)),
      );
    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        canvas.drawPath(metric.extractPath(distance, distance + 6), paint);
        distance += 10;
      }
    }
  }

  @override
  bool shouldRepaint(_DashedBorderPainter oldDelegate) =>
      oldDelegate.color != color;
}
