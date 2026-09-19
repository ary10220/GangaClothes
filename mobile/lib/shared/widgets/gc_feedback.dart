import 'package:flutter/material.dart';

import '../../app/theme.dart';
import 'gc_button.dart';

enum GcFeedbackVariant { neutral, success, error }

class GcFeedback extends StatelessWidget {
  const GcFeedback({
    required this.message,
    this.variant = GcFeedbackVariant.neutral,
    this.onDismiss,
    this.actionLabel,
    this.onAction,
    super.key,
  });

  final String message;
  final GcFeedbackVariant variant;
  final VoidCallback? onDismiss;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final colors = switch (variant) {
      GcFeedbackVariant.neutral => (
        GangaColors.soft,
        GangaColors.gray,
        Icons.info_outline,
      ),
      GcFeedbackVariant.success => (
        GangaColors.lightSuccess,
        GangaColors.success,
        Icons.check_circle_outline,
      ),
      GcFeedbackVariant.error => (
        GangaColors.lightError,
        GangaColors.alert,
        Icons.error_outline,
      ),
    };
    return Semantics(
      container: true,
      liveRegion: true,
      label: message,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
        decoration: BoxDecoration(
          color: colors.$1,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: colors.$2.withValues(alpha: 0.35)),
        ),
        child: Wrap(
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 8,
          runSpacing: 6,
          children: [
            Icon(colors.$3, size: 18, color: colors.$2),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 260),
              child: Text(
                message,
                style: TextStyle(color: colors.$2, fontSize: 12),
              ),
            ),
            if (actionLabel != null && onAction != null)
              GcButton(
                label: actionLabel!,
                variant: GcButtonVariant.outlined,
                onPressed: onAction,
              ),
            if (onDismiss != null)
              IconButton(
                onPressed: onDismiss,
                tooltip: 'Dismiss',
                icon: Icon(Icons.close, color: colors.$2),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(minWidth: 44, minHeight: 44),
              ),
          ],
        ),
      ),
    );
  }
}
