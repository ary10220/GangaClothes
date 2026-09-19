import 'package:flutter/material.dart';

import '../../app/theme.dart';

class AuthLayout extends StatelessWidget {
  const AuthLayout({
    required this.title,
    required this.brandDescription,
    required this.brandEyebrow,
    required this.content,
    this.footer,
    super.key,
  });

  final String title;
  final String brandDescription;
  final String brandEyebrow;
  final Widget content;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GangaColors.paper,
      body: SafeArea(
        child: Builder(
          builder: (context) {
            final width = MediaQuery.sizeOf(context).width;
            final wide = width >= 720;
            const scrollPadding = EdgeInsets.symmetric(
              horizontal: 18,
              vertical: 28,
            );
            final card = SizedBox(
              width: (width - scrollPadding.horizontal).clamp(0.0, 880.0),
              child: Container(
                decoration: BoxDecoration(
                  color: GangaColors.white,
                  border: Border.all(color: GangaColors.ink, width: 2),
                  borderRadius: BorderRadius.circular(16),
                  boxShadow: [
                    BoxShadow(
                      color: GangaColors.ink.withValues(alpha: 0.13),
                      blurRadius: 22,
                      offset: const Offset(0, 10),
                    ),
                  ],
                ),
                clipBehavior: Clip.antiAlias,
                child: wide
                    ? IntrinsicHeight(
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(
                              child: _BrandPanel(
                                description: brandDescription,
                                eyebrow: brandEyebrow,
                              ),
                            ),
                            Expanded(
                              child: _FormPanel(
                                title: title,
                                content: content,
                                footer: footer,
                              ),
                            ),
                          ],
                        ),
                      )
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _BrandPanel(
                            description: brandDescription,
                            eyebrow: brandEyebrow,
                          ),
                          _FormPanel(
                            title: title,
                            content: content,
                            footer: footer,
                          ),
                        ],
                      ),
              ),
            );

            return SingleChildScrollView(
              padding: scrollPadding,
              child: Center(child: card),
            );
          },
        ),
      ),
    );
  }
}

class _BrandPanel extends StatelessWidget {
  const _BrandPanel({required this.description, required this.eyebrow});

  final String description;
  final String eyebrow;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    color: GangaColors.ink,
    padding: const EdgeInsets.all(32),
    child: Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(
          Icons.checkroom_outlined,
          color: GangaColors.brand,
          size: 52,
        ),
        const SizedBox(height: 14),
        RichText(
          text: TextSpan(
            style: GangaTextStyles.brandWordmark.copyWith(
              color: GangaColors.white,
            ),
            children: const [
              TextSpan(text: 'Ganga'),
              TextSpan(
                text: 'Clothes',
                style: TextStyle(color: GangaColors.brand),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        Text(
          description,
          style: const TextStyle(
            color: Color(0xFFB9BDC4),
            fontSize: 13,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 22),
        Text(
          eyebrow,
          style: const TextStyle(
            color: Color(0xFF8B929C),
            fontSize: 10,
            letterSpacing: 1.2,
          ),
        ),
      ],
    ),
  );
}

class _FormPanel extends StatelessWidget {
  const _FormPanel({required this.title, required this.content, this.footer});

  final String title;
  final Widget content;
  final Widget? footer;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(28),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(title, style: GangaTextStyles.heading),
        const SizedBox(height: 18),
        content,
        if (footer != null) ...[const SizedBox(height: 12), footer!],
      ],
    ),
  );
}
