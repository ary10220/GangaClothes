import 'package:flutter/material.dart';

import '../../app/theme.dart';

class GcChip extends StatelessWidget {
  const GcChip({
    required this.label,
    this.selected = false,
    this.onTap,
    this.semanticLabel,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final foreground = selected ? GangaColors.white : GangaColors.gray;
    return Semantics(
      button: onTap != null,
      toggled: selected,
      enabled: onTap != null,
      label: semanticLabel ?? label,
      child: ExcludeSemantics(
        child: Material(
          color: selected ? GangaColors.ink : GangaColors.white,
          shape: StadiumBorder(
            side: BorderSide(
              color: selected ? GangaColors.ink : GangaColors.line,
              width: 1.5,
            ),
          ),
          child: InkWell(
            onTap: onTap,
            customBorder: const StadiumBorder(),
            child: ConstrainedBox(
              constraints: const BoxConstraints(minHeight: 44),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Center(
                  child: Text(
                    label,
                    style: TextStyle(fontSize: 11.5, color: foreground),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
