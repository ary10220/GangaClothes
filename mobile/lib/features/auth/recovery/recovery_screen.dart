import 'dart:async';

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

class RecoveryScreen extends StatefulWidget {
  const RecoveryScreen({
    required this.authService,
    this.initialEmail,
    super.key,
  });

  final AuthService authService;
  final String? initialEmail;

  @override
  State<RecoveryScreen> createState() => _RecoveryScreenState();
}

class _RecoveryScreenState extends State<RecoveryScreen> {
  final _email = TextEditingController();
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirmation = TextEditingController();
  final _emailFormKey = GlobalKey<FormState>();
  final _codeFormKey = GlobalKey<FormState>();
  Timer? _timer;
  bool _codeStep = false;
  bool _submitting = false;
  int _minutes = 15;
  int _cooldown = 0;
  String? _detail;
  String? _error;

  @override
  void initState() {
    super.initState();
    _email.text = widget.initialEmail ?? '';
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final controller in [_email, _code, _password, _confirmation]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _requestCode({bool resend = false}) async {
    if (_submitting || (resend && _cooldown > 0)) return;
    setState(() => _error = null);
    if (!(_emailFormKey.currentState?.validate() ?? false)) return;

    setState(() => _submitting = true);
    try {
      final result = await widget.authService.requestRecovery(
        _email.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _codeStep = true;
        _minutes = result.minutes;
        _detail = result.detail;
        _code.clear();
      });
      _startCooldown(result.resendAfter);
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'No se pudo enviar el código. Intenta de nuevo.',
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _resetPassword() async {
    if (_submitting) return;
    setState(() => _error = null);
    if (!(_codeFormKey.currentState?.validate() ?? false)) return;

    setState(() => _submitting = true);
    try {
      await widget.authService.resetPassword(
        email: _email.text.trim(),
        code: _code.text.trim(),
        password: _password.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Tu contraseña se actualizó. Inicia sesión con la nueva.',
          ),
        ),
      );
      Navigator.of(context).pushReplacementNamed(
        AppRoutes.login,
        arguments: AuthRouteArguments(email: _email.text.trim()),
      );
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = 'No se pudo cambiar la contraseña. Intenta de nuevo.',
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _useAnotherEmail() {
    _timer?.cancel();
    setState(() {
      _codeStep = false;
      _cooldown = 0;
      _detail = null;
      _error = null;
    });
  }

  void _startCooldown(int seconds) {
    _timer?.cancel();
    setState(() => _cooldown = seconds.clamp(0, 3600));
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() => _cooldown = (_cooldown - 1).clamp(0, 3600));
      if (_cooldown == 0) timer.cancel();
    });
  }

  @override
  Widget build(BuildContext context) => AuthLayout(
    title: _codeStep ? 'Revisa tu correo' : 'Recuperar contraseña',
    brandDescription:
        'Te enviamos un código a tu correo para que crees una contraseña nueva. Tu cuenta, reservas y compras siguen igual.',
    brandEyebrow: 'recuperar acceso · paso ${_codeStep ? 2 : 1} de 2',
    content: _codeStep ? _buildCodeStep() : _buildEmailStep(),
    footer: Wrap(
      alignment: WrapAlignment.center,
      children: [
        TextButton(
          onPressed: _submitting
              ? null
              : () => Navigator.of(context).pushReplacementNamed(
                  AppRoutes.login,
                  arguments: AuthRouteArguments(email: _email.text.trim()),
                ),
          child: const Text('← Volver a iniciar sesión'),
        ),
      ],
    ),
  );

  Widget _buildEmailStep() => Form(
    key: _emailFormKey,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Escribe el correo con el que te registraste y te enviaremos un código de 6 dígitos.',
          style: TextStyle(
            color: Color(0xFF6B6F76),
            fontSize: 12.5,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 16),
        GcField(
          label: 'Correo electrónico',
          hint: 'tu@correo.com',
          controller: _email,
          enabled: !_submitting,
          keyboardType: TextInputType.emailAddress,
          validator: (value) =>
              !isValidEmail(value ?? '') ? 'Ingresa un correo válido.' : null,
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          GcFeedback(message: _error!, variant: GcFeedbackVariant.error),
        ],
        const SizedBox(height: 12),
        GcButton(
          label: _submitting ? 'Enviando…' : 'Enviar código',
          loading: _submitting,
          expand: true,
          onPressed: _submitting ? null : _requestCode,
        ),
      ],
    ),
  );

  Widget _buildCodeStep() => Form(
    key: _codeFormKey,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${_detail ?? 'Si el correo tiene una cuenta, te llegó un código de 6 dígitos.'} Vence en $_minutes minutos. Si no lo ves, revisa la carpeta de spam.',
          style: const TextStyle(
            color: Color(0xFF6B6F76),
            fontSize: 12.5,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 16),
        GcField(
          label: 'Código de 6 dígitos',
          hint: '000000',
          controller: _code,
          enabled: !_submitting,
          keyboardType: TextInputType.number,
          textInputAction: TextInputAction.next,
          validator: (value) =>
              !RegExp(r'^\d{6}$').hasMatch(value?.trim() ?? '')
              ? 'El código son 6 números.'
              : null,
        ),
        const SizedBox(height: 14),
        GcField(
          label: 'Contraseña nueva',
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
          label: 'Repetir contraseña',
          controller: _confirmation,
          enabled: !_submitting,
          obscureText: true,
          textInputAction: TextInputAction.done,
          validator: (value) {
            if (value == null || value.isEmpty) return 'Repite la contraseña.';
            return value == _password.text
                ? null
                : 'Las contraseñas no coinciden.';
          },
          onFieldSubmitted: (_) => _resetPassword(),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          GcFeedback(message: _error!, variant: GcFeedbackVariant.error),
        ],
        const SizedBox(height: 12),
        GcButton(
          label: _submitting ? 'Guardando…' : 'Cambiar contraseña',
          loading: _submitting,
          expand: true,
          onPressed: _submitting ? null : _resetPassword,
        ),
        const SizedBox(height: 12),
        Center(
          child: Wrap(
            alignment: WrapAlignment.center,
            children: [
              const Text('¿No llegó? ', style: TextStyle(fontSize: 12)),
              if (_cooldown > 0)
                Text(
                  'Puedes pedir otro en $_cooldown s',
                  style: const TextStyle(fontSize: 12),
                )
              else
                TextButton(
                  onPressed: _submitting
                      ? null
                      : () => _requestCode(resend: true),
                  child: const Text('Reenviar código'),
                ),
              const Text(' · ', style: TextStyle(fontSize: 12)),
              TextButton(
                onPressed: _submitting ? null : _useAnotherEmail,
                child: const Text('Usar otro correo'),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}
