import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../features/auth/session_model.dart';
import '../../shared/widgets/gc_app_bar.dart';
import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_chip.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_field.dart';
import '../../shared/widgets/gc_loading_empty_error.dart';
import '../../shared/widgets/gc_status_badge.dart';

class ThemeShowcaseScreen extends StatefulWidget {
  const ThemeShowcaseScreen({
    required this.routeName,
    required this.session,
    this.returnTo,
    this.onLogout,
    super.key,
  });

  final String routeName;
  final Session? session;
  final String? returnTo;
  final VoidCallback? onLogout;

  @override
  State<ThemeShowcaseScreen> createState() => _ThemeShowcaseScreenState();
}

class _ThemeShowcaseScreenState extends State<ThemeShowcaseScreen> {
  late final TextEditingController _controller;
  bool _selected = true;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: 'demo@example.com');
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: GcAppBar(
        destinations: [
          GcAppBarDestination(
            label: 'Catalog',
            onPressed: () {},
            selected: true,
          ),
          GcAppBarDestination(label: 'Reservations', onPressed: () {}),
          GcAppBarDestination(label: 'Cart', onPressed: () {}),
        ],
        accountName: widget.session?.user.fullName,
        accountRole: widget.session?.user.roles.firstOrNull,
        onAccountPressed: widget.session == null ? null : () {},
        onLogout: widget.onLogout,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 22, 20, 40),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('PHASE 3 SHOWCASE', style: GangaTextStyles.eyebrow),
              const SizedBox(height: 8),
              const Text(
                'Shared visual primitives',
                style: GangaTextStyles.heading,
              ),
              const SizedBox(height: 8),
              Text(
                'Ruta preparada: ${widget.routeName}',
                style: GangaTextStyles.metadata,
              ),
              if (widget.returnTo != null) ...[
                const SizedBox(height: 4),
                Text(
                  'Destino pendiente: ${widget.returnTo}',
                  style: GangaTextStyles.metadata,
                ),
              ],
              if (widget.session != null) ...[
                const SizedBox(height: 4),
                Text('Sesión activa: ${widget.session!.user.fullName}'),
              ],
              const SizedBox(height: 26),
              _Section(
                title: 'Actions',
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    const GcButton(label: 'Primary', onPressed: _noop),
                    const GcButton(
                      label: 'Secondary',
                      variant: GcButtonVariant.secondary,
                      onPressed: _noop,
                    ),
                    const GcButton(
                      label: 'Outlined',
                      variant: GcButtonVariant.outlined,
                      onPressed: _noop,
                    ),
                    const GcButton(
                      label: 'Danger',
                      variant: GcButtonVariant.danger,
                      onPressed: _noop,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _Section(
                title: 'Field and filters',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    GcField(
                      label: 'Email',
                      hint: 'name@example.com',
                      controller: _controller,
                      errorText: 'Example validation error.',
                      keyboardType: TextInputType.emailAddress,
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        GcChip(
                          label: 'Selected',
                          selected: _selected,
                          onTap: () => setState(() => _selected = !_selected),
                        ),
                        const GcChip(label: 'Unselected'),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _Section(
                title: 'Statuses and surfaces',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        GcStatusBadge(
                          text: 'AVAILABLE',
                          variant: GcStatusBadgeVariant.success,
                        ),
                        GcStatusBadge(
                          text: 'ERROR',
                          variant: GcStatusBadgeVariant.error,
                        ),
                        GcStatusBadge(
                          text: 'PENDING',
                          variant: GcStatusBadgeVariant.brand,
                        ),
                        GcStatusBadge(text: 'NEUTRAL'),
                      ],
                    ),
                    const SizedBox(height: 14),
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'White bordered card',
                              style: GangaTextStyles.subheading,
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              'Bs 149,90',
                              style: GangaTextStyles.money,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Metadata and supporting copy',
                              style: GangaTextStyles.metadata,
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(22),
                      decoration: BoxDecoration(
                        color: GangaColors.white,
                        border: Border.all(color: GangaColors.ink, width: 2),
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                            color: GangaColors.ink.withValues(alpha: 0.18),
                            blurRadius: 18,
                            offset: const Offset(0, 8),
                          ),
                        ],
                      ),
                      child: const Text(
                        'Modal / sheet-like surface',
                        style: GangaTextStyles.subheading,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _Section(
                title: 'Loading, empty, and error',
                child: Column(
                  children: [
                    const GcLoadingEmptyError(state: GcPanelState.loading),
                    const SizedBox(height: 10),
                    const GcLoadingEmptyError(
                      state: GcPanelState.empty,
                      emptyTitle: 'No products yet',
                      emptyMessage: 'Try another filter.',
                    ),
                    const SizedBox(height: 10),
                    GcLoadingEmptyError(
                      state: GcPanelState.error,
                      errorTitle: 'Server error',
                      errorMessage: 'The content could not be loaded.',
                      onRetry: _noop,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              _Section(
                title: 'Feedback',
                child: const Column(
                  children: [
                    GcFeedback(message: 'Neutral inline feedback.'),
                    SizedBox(height: 8),
                    GcFeedback(
                      message: 'Saved successfully.',
                      variant: GcFeedbackVariant.success,
                    ),
                    SizedBox(height: 8),
                    GcFeedback(
                      message: 'Something went wrong.',
                      variant: GcFeedbackVariant.error,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(title.toUpperCase(), style: GangaTextStyles.label),
      const SizedBox(height: 8),
      child,
    ],
  );
}

void _noop() {}
