import 'package:flutter/material.dart';

import '../../app/theme.dart';

enum GcButtonVariant { primary, secondary, outlined, danger }

class GcButton extends StatelessWidget {
  const GcButton({
    required this.label,
    required this.onPressed,
    this.variant = GcButtonVariant.primary,
    this.loading = false,
    this.semanticLabel,
    this.icon,
    this.expand = false,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final GcButtonVariant variant;
  final bool loading;
  final String? semanticLabel;
  final Widget? icon;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null && !loading;
    final button = switch (variant) {
      GcButtonVariant.outlined => OutlinedButton(
        onPressed: enabled ? onPressed : null,
        style: _outlinedStyle(),
        child: _content(context),
      ),
      GcButtonVariant.primary ||
      GcButtonVariant.secondary ||
      GcButtonVariant.danger => FilledButton(
        onPressed: enabled ? onPressed : null,
        style: _filledStyle(),
        child: _content(context),
      ),
    };

    return Semantics(
      button: true,
      enabled: enabled,
      label: semanticLabel ?? label,
      child: expand
          ? SizedBox(
              width: double.infinity,
              child: ExcludeSemantics(child: button),
            )
          : ExcludeSemantics(child: button),
    );
  }

  Widget _content(BuildContext context) {
    final children = <Widget>[
      if (loading)
        const SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      if (icon != null && !loading) icon!,
      Flexible(child: Text(label, textAlign: TextAlign.center)),
    ];
    return Row(mainAxisSize: MainAxisSize.min, children: children);
  }

  ButtonStyle _filledStyle() {
    final background = switch (variant) {
      GcButtonVariant.primary => GangaColors.brand,
      GcButtonVariant.secondary => GangaColors.ink,
      GcButtonVariant.danger => GangaColors.alert,
      GcButtonVariant.outlined => GangaColors.white,
    };
    return ButtonStyle(
      minimumSize: const WidgetStatePropertyAll(Size(0, 48)),
      backgroundColor: WidgetStateProperty.resolveWith(
        (states) => states.contains(WidgetState.disabled)
            ? background.withValues(alpha: 0.45)
            : background,
      ),
      foregroundColor: const WidgetStatePropertyAll(GangaColors.white),
      overlayColor: WidgetStatePropertyAll(
        GangaColors.white.withValues(alpha: 0.12),
      ),
      textStyle: const WidgetStatePropertyAll(
        TextStyle(inherit: false, fontSize: 12.5, fontWeight: FontWeight.w700),
      ),
      padding: const WidgetStatePropertyAll(
        EdgeInsets.symmetric(horizontal: 16, vertical: 9),
      ),
      shape: WidgetStatePropertyAll(
        RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  ButtonStyle _outlinedStyle() => ButtonStyle(
    minimumSize: const WidgetStatePropertyAll(Size(0, 48)),
    foregroundColor: const WidgetStatePropertyAll(GangaColors.ink),
    textStyle: const WidgetStatePropertyAll(
      TextStyle(inherit: false, fontSize: 12.5, fontWeight: FontWeight.w700),
    ),
    backgroundColor: WidgetStateProperty.resolveWith(
      (states) => states.contains(WidgetState.disabled)
          ? GangaColors.white.withValues(alpha: 0.45)
          : GangaColors.white,
    ),
    side: WidgetStateProperty.resolveWith(
      (states) => BorderSide(
        color: states.contains(WidgetState.disabled)
            ? GangaColors.line.withValues(alpha: 0.45)
            : GangaColors.ink,
        width: 1.5,
      ),
    ),
    padding: const WidgetStatePropertyAll(
      EdgeInsets.symmetric(horizontal: 16, vertical: 9),
    ),
    shape: WidgetStatePropertyAll(
      RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
    ),
  );
}
