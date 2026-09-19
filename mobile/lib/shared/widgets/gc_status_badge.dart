import 'package:flutter/material.dart';

import '../../app/theme.dart';

enum GcStatusBadgeVariant { success, error, brand, neutral }

class GcStatusBadge extends StatelessWidget {
  const GcStatusBadge({
    required this.text,
    this.variant = GcStatusBadgeVariant.neutral,
    this.semanticLabel,
    super.key,
  });

  final String text;
  final GcStatusBadgeVariant variant;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final colors = switch (variant) {
      GcStatusBadgeVariant.success => (
        GangaColors.lightSuccess,
        GangaColors.success,
      ),
      GcStatusBadgeVariant.error => (GangaColors.lightError, GangaColors.alert),
      GcStatusBadgeVariant.brand => (GangaColors.lightBrand, GangaColors.brand),
      GcStatusBadgeVariant.neutral => (GangaColors.soft, GangaColors.gray),
    };
    return Semantics(
      label: semanticLabel ?? text,
      container: true,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: colors.$1,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
          child: Text(
            text,
            style: TextStyle(
              fontFamily: 'monospace',
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: colors.$2,
            ),
          ),
        ),
      ),
    );
  }
}
