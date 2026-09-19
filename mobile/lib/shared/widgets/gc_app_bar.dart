import 'package:flutter/material.dart';

import '../../app/theme.dart';

class GcAppBarDestination {
  const GcAppBarDestination({
    required this.label,
    required this.onPressed,
    this.selected = false,
    this.semanticLabel,
  });

  final String label;
  final VoidCallback onPressed;
  final bool selected;
  final String? semanticLabel;
}

class GcAppBar extends StatelessWidget implements PreferredSizeWidget {
  const GcAppBar({
    this.destinations = const [],
    this.accountName,
    this.accountRole,
    this.onAccountPressed,
    this.onLogout,
    this.leading,
    this.trailing,
    this.height = 68,
    super.key,
  });

  final List<GcAppBarDestination> destinations;
  final String? accountName;
  final String? accountRole;
  final VoidCallback? onAccountPressed;
  final VoidCallback? onLogout;
  final Widget? leading;
  final Widget? trailing;
  final double height;

  @override
  Size get preferredSize => Size.fromHeight(height);

  @override
  Widget build(BuildContext context) {
    return Material(
      color: GangaColors.white,
      child: SafeArea(
        bottom: false,
        child: Container(
          height: height,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: const BoxDecoration(
            border: Border(
              bottom: BorderSide(color: GangaColors.line, width: 1.5),
            ),
          ),
          child: Row(
            children: [
              ?leading,
              Semantics(
                header: true,
                label: 'GangaClothes',
                child: Text(
                  'GangaClothes',
                  style: GangaTextStyles.brandWordmark,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      for (final destination in destinations) ...[
                        _DestinationButton(destination: destination),
                        const SizedBox(width: 4),
                      ],
                      if (accountName != null && onAccountPressed != null)
                        Semantics(
                          button: true,
                          label:
                              '${accountName!}${accountRole == null ? '' : ', $accountRole'}',
                          child: ExcludeSemantics(
                            child: TextButton(
                              onPressed: onAccountPressed,
                              style: TextButton.styleFrom(
                                minimumSize: const Size(48, 48),
                                foregroundColor: GangaColors.ink,
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 8,
                                ),
                                textStyle: const TextStyle(
                                  inherit: false,
                                  fontSize: 12,
                                ),
                              ),
                              child: Text(
                                accountRole == null
                                    ? accountName!
                                    : '$accountName · $accountRole',
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ),
                        ),
                      if (onLogout != null)
                        IconButton(
                          onPressed: onLogout,
                          tooltip: 'Log out',
                          icon: const Icon(Icons.logout),
                          constraints: const BoxConstraints(
                            minWidth: 48,
                            minHeight: 48,
                          ),
                        ),
                      ?trailing,
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DestinationButton extends StatelessWidget {
  const _DestinationButton({required this.destination});

  final GcAppBarDestination destination;

  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: destination.selected,
    label: destination.semanticLabel ?? destination.label,
    child: ExcludeSemantics(
      child: TextButton(
        onPressed: destination.onPressed,
        style: TextButton.styleFrom(
          minimumSize: const Size(48, 48),
          padding: const EdgeInsets.symmetric(horizontal: 8),
          foregroundColor: destination.selected
              ? GangaColors.ink
              : GangaColors.gray,
          textStyle: const TextStyle(
            inherit: false,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: destination.selected
                ? const BorderSide(color: GangaColors.brand, width: 1.5)
                : BorderSide.none,
          ),
        ),
        child: Text(destination.label),
      ),
    ),
  );
}
