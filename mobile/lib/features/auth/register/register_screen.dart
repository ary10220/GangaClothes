import 'package:flutter/material.dart';

import '../../../app/routes.dart';
import '../../../core/network/api_error.dart';
import '../../../shared/widgets/gc_button.dart';
import '../../../shared/widgets/gc_feedback.dart';
import '../../../shared/widgets/gc_field.dart';
import '../auth_layout.dart';
import '../auth_service.dart';
import '../auth_validation.dart';
import '../password_rules_view.dart';
import '../session_model.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({
    required this.authService,
    this.onSessionChanged,
    this.returnTo,
    super.key,
  });

  final AuthService authService;
  final ValueChanged<Session>? onSessionChanged;
  final String? returnTo;

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _lastName = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _confirmation = TextEditingController();
  bool _submitting = false;
  String? _error;
  bool _duplicateEmail = false;

  @override
  void dispose() {
    for (final controller in [
      _name,
      _lastName,
      _email,
      _phone,
      _password,
      _confirmation,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    setState(() {
      _error = null;
      _duplicateEmail = false;
    });
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _submitting = true);
    try {
      final session = await widget.authService.register(
        RegisterRequest(
          name: _name.text.trim(),
          lastName: _lastName.text.trim().isEmpty
              ? null
              : _lastName.text.trim(),
          email: _email.text.trim(),
          password: _password.text,
          phone: _phone.text.trim().isEmpty ? null : _phone.text.trim(),
        ),
      );
      widget.onSessionChanged?.call(session);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Cuenta creada. Hola, ${session.user.name}.')),
      );
      final destination =
          AppRoutes.safeReturnTo(widget.returnTo) ?? AppRoutes.catalog;
      Navigator.of(context).pushReplacementNamed(destination);
    } on ApiError catch (error) {
      if (!mounted) return;
      final duplicate =
          error.statusCode == 400 &&
          RegExp(
            r'correo|cuenta',
            caseSensitive: false,
          ).hasMatch(error.message);
      setState(() {
        _duplicateEmail = duplicate;
        _error = error.message.isNotEmpty
            ? error.message
            : 'No se pudo crear la cuenta. Intenta de nuevo.';
      });
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'No se pudo crear la cuenta. Intenta de nuevo.',
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) => AuthLayout(
    title: 'Crear cuenta',
    brandDescription:
        'Con tu cuenta puedes reservar prendas para probártelas en la sucursal que elijas y comprar en línea.',
    brandEyebrow: 'cuenta de cliente',
    content: Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          GcField(
            label: 'Nombre *',
            controller: _name,
            enabled: !_submitting,
            textInputAction: TextInputAction.next,
            validator: (value) =>
                !isValidName(value ?? '') ? 'Ingresa tu nombre.' : null,
          ),
          const SizedBox(height: 14),
          GcField(
            label: 'Apellido',
            controller: _lastName,
            enabled: !_submitting,
            textInputAction: TextInputAction.next,
            validator: (value) => (value?.trim().length ?? 0) > 100
                ? 'Máximo 100 caracteres.'
                : null,
          ),
          const SizedBox(height: 14),
          GcField(
            label: 'Correo electrónico *',
            hint: 'tu@correo.com',
            controller: _email,
            enabled: !_submitting,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            validator: (value) =>
                !isValidEmail(value ?? '') ? 'Ingresa un correo válido.' : null,
          ),
          if (_duplicateEmail) ...[
            const SizedBox(height: 5),
            TextButton(
              onPressed: _submitting
                  ? null
                  : () => Navigator.of(context).pushReplacementNamed(
                      AppRoutes.login,
                      arguments: AuthRouteArguments(
                        returnTo: AppRoutes.safeReturnTo(widget.returnTo),
                        email: _email.text.trim(),
                      ),
                    ),
              child: const Text('Iniciar sesión con este correo →'),
            ),
          ],
          const SizedBox(height: 5),
          GcField(
            label: 'Teléfono',
            hint: '70012345',
            controller: _phone,
            enabled: !_submitting,
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.next,
            validator: (value) => !isValidPhone(value ?? '')
                ? 'Solo números, espacios, + o -, entre 6 y 20 caracteres.'
                : null,
          ),
          const SizedBox(height: 4),
          const Text(
            'La sucursal te avisa por este número cuando tu reserva está lista.',
            style: TextStyle(color: Color(0xFF6B6F76), fontSize: 11.5),
          ),
          const SizedBox(height: 14),
          GcField(
            label: 'Contraseña *',
            controller: _password,
            enabled: !_submitting,
            obscureText: true,
            textInputAction: TextInputAction.next,
            onChanged: (_) => setState(() {}),
            validator: (value) => passwordError(value ?? ''),
          ),
          const SizedBox(height: 7),
          PasswordRulesView(value: _password.text),
          const SizedBox(height: 10),
          GcField(
            label: 'Repetir contraseña *',
            controller: _confirmation,
            enabled: !_submitting,
            obscureText: true,
            textInputAction: TextInputAction.done,
            validator: (value) {
              if (value == null || value.isEmpty) {
                return 'Repite la contraseña.';
              }
              return value == _password.text
                  ? null
                  : 'Las contraseñas no coinciden.';
            },
            onFieldSubmitted: (_) => _submit(),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            GcFeedback(message: _error!, variant: GcFeedbackVariant.error),
          ],
          const SizedBox(height: 12),
          GcButton(
            label: _submitting ? 'Creando cuenta…' : 'Crear cuenta',
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
          const Text('¿Ya tienes cuenta?'),
          TextButton(
            onPressed: _submitting
                ? null
                : () => Navigator.of(context).pushReplacementNamed(
                    AppRoutes.login,
                    arguments: AuthRouteArguments(
                      returnTo: AppRoutes.safeReturnTo(widget.returnTo),
                    ),
                  ),
            child: const Text('Iniciar sesión'),
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
