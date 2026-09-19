import 'package:flutter/material.dart';

import '../../../app/routes.dart';
import '../../../core/network/api_error.dart';
import '../../../shared/widgets/gc_button.dart';
import '../../../shared/widgets/gc_feedback.dart';
import '../../../shared/widgets/gc_field.dart';
import '../auth_layout.dart';
import '../auth_service.dart';
import '../auth_validation.dart';
import '../session_model.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    required this.authService,
    this.onSessionChanged,
    this.returnTo,
    this.initialEmail,
    super.key,
  });

  final AuthService authService;
  final ValueChanged<Session>? onSessionChanged;
  final String? returnTo;
  final String? initialEmail;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _email;
  late final TextEditingController _password;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _email = TextEditingController(text: widget.initialEmail ?? '');
    _password = TextEditingController();
  }

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    setState(() => _error = null);
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _submitting = true);
    try {
      final session = await widget.authService.login(
        _email.text.trim(),
        _password.text,
      );
      widget.onSessionChanged?.call(session);
      if (!mounted) return;
      final destination =
          AppRoutes.safeReturnTo(widget.returnTo) ?? AppRoutes.catalog;
      Navigator.of(context).pushReplacementNamed(destination);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.statusCode == 401
            ? 'Correo o contrasena incorrectos.'
            : error.message.isNotEmpty
            ? error.message
            : 'No se pudo iniciar sesión. Intenta de nuevo.';
      });
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'No se pudo iniciar sesión. Intenta de nuevo.');
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _open(String route, {String? email}) {
    Navigator.of(context).pushNamed(
      route,
      arguments: AuthRouteArguments(
        returnTo: AppRoutes.safeReturnTo(widget.returnTo),
        email: email,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AuthLayout(
      title: 'Bienvenido de vuelta',
      brandDescription:
          'Catálogo por temporadas, reservas para el vestidor, probador virtual y ventas en un solo lugar.',
      brandEyebrow: 'roles · administrador / encargado / cajero / cliente',
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            GcField(
              label: 'Correo electrónico',
              hint: 'tu@correo.com',
              controller: _email,
              enabled: !_submitting,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              validator: (value) => !isValidEmail(value ?? '')
                  ? 'Ingresa un correo válido.'
                  : null,
            ),
            const SizedBox(height: 14),
            GcField(
              label: 'Contraseña',
              hint: '••••••••',
              controller: _password,
              enabled: !_submitting,
              obscureText: true,
              textInputAction: TextInputAction.done,
              validator: (value) => !isValidLoginPassword(value ?? '')
                  ? 'La contraseña debe tener al menos 6 caracteres.'
                  : null,
              onFieldSubmitted: (_) => _submit(),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _submitting
                    ? null
                    : () => _open(
                        AppRoutes.recovery,
                        email: isValidEmail(_email.text)
                            ? _email.text.trim()
                            : null,
                      ),
                child: const Text('¿Olvidaste tu contraseña?'),
              ),
            ),
            if (_error != null) ...[
              GcFeedback(message: _error!, variant: GcFeedbackVariant.error),
              const SizedBox(height: 12),
            ],
            GcButton(
              label: _submitting ? 'Verificando…' : 'Iniciar sesión',
              loading: _submitting,
              expand: true,
              onPressed: _submitting ? null : _submit,
            ),
          ],
        ),
      ),
      footer: SizedBox(
        width: double.infinity,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Text('¿Cliente nuevo?'),
            TextButton(
              onPressed: _submitting ? null : () => _open(AppRoutes.register),
              child: const Text('Crear cuenta'),
            ),
            TextButton(
              onPressed: _submitting
                  ? null
                  : () => Navigator.of(
                      context,
                    ).pushReplacementNamed(AppRoutes.catalog),
              child: const Text('Ver el catálogo'),
            ),
          ],
        ),
      ),
    );
  }
}
