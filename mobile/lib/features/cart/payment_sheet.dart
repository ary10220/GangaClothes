import 'package:flutter/material.dart';

import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_field.dart';
import 'cart_controller.dart';
import 'cart_models.dart';

class PaymentSheet extends StatefulWidget {
  const PaymentSheet({
    required this.controller,
    required this.initialHolder,
    super.key,
  });

  final CartController controller;
  final String initialHolder;

  @override
  State<PaymentSheet> createState() => _PaymentSheetState();
}

class _PaymentSheetState extends State<PaymentSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _number;
  late final TextEditingController _holder;
  late final TextEditingController _expiry;
  late final TextEditingController _cvc;
  bool _simulateFailure = false;
  bool _attempted = false;

  @override
  void initState() {
    super.initState();
    _number = TextEditingController(text: '4242 4242 4242 4242');
    _holder = TextEditingController(text: widget.initialHolder);
    _expiry = TextEditingController(text: '12/30');
    _cvc = TextEditingController(text: '123');
    widget.controller.addListener(_onControllerChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onControllerChanged);
    for (final field in [_number, _holder, _expiry, _cvc]) {
      field.dispose();
    }
    super.dispose();
  }

  void _onControllerChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _submit() async {
    setState(() => _attempted = true);
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final result = await widget.controller.checkout(
      simulateFailure: _simulateFailure,
    );
    if (result != null && mounted) Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final cart = widget.controller.pendingSale ?? widget.controller.cart;
    if (cart == null) return const SizedBox.shrink();
    final processing = widget.controller.paymentProcessing;
    return SafeArea(
      child: SingleChildScrollView(
        padding: EdgeInsets.fromLTRB(
          20,
          18,
          20,
          20 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 42,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(99),
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Text('PASARELA DE PAGO · MODO PRUEBA'),
              const SizedBox(height: 4),
              Text(
                'Pagar Bs ${formatCartMoney(cart.total)}',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 5),
              const Text(
                'Los datos de tarjeta son solo de prueba y nunca se envían al servidor ni se guardan.',
              ),
              const SizedBox(height: 16),
              GcField(
                label: 'Número de tarjeta',
                controller: _number,
                enabled: !processing,
                keyboardType: TextInputType.number,
                validator: (value) =>
                    _attempted ? validateCardNumber(value ?? '') : null,
              ),
              const SizedBox(height: 12),
              GcField(
                label: 'Titular',
                controller: _holder,
                enabled: !processing,
                validator: (value) =>
                    _attempted ? validateCardHolder(value ?? '') : null,
              ),
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: GcField(
                      label: 'Vence (MM/AA)',
                      controller: _expiry,
                      enabled: !processing,
                      keyboardType: TextInputType.datetime,
                      validator: (value) =>
                          _attempted ? validateCardExpiry(value ?? '') : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: GcField(
                      label: 'CVC',
                      controller: _cvc,
                      enabled: !processing,
                      keyboardType: TextInputType.number,
                      validator: (value) =>
                          _attempted ? validateCvc(value ?? '') : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: _simulateFailure,
                enabled: !processing,
                onChanged: (value) =>
                    setState(() => _simulateFailure = value ?? false),
                title: const Text(
                  'Simular tarjeta rechazada (prueba)',
                  style: TextStyle(fontSize: 12),
                ),
                controlAffinity: ListTileControlAffinity.leading,
              ),
              if (widget.controller.paymentError != null) ...[
                const SizedBox(height: 4),
                GcFeedback(
                  message: widget.controller.paymentError!,
                  variant: GcFeedbackVariant.error,
                ),
              ],
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: GcButton(
                      label: 'Cancelar',
                      variant: GcButtonVariant.outlined,
                      onPressed: processing
                          ? null
                          : () => Navigator.of(context).pop(),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: GcButton(
                      label: processing ? 'Procesando…' : 'Pagar',
                      loading: processing,
                      variant: GcButtonVariant.primary,
                      onPressed: processing ? null : _submit,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String? validateCardNumber(String value) {
  return RegExp(r'^\d{16}$').hasMatch(value.replaceAll(' ', ''))
      ? null
      : 'El número tiene 16 dígitos.';
}

String? validateCardHolder(String value) =>
    value.trim().isEmpty ? 'Escribe el nombre del titular.' : null;

String? validateCardExpiry(String value, {DateTime? now}) {
  final match = RegExp(r'^(0[1-9]|1[0-2])/(\d{2})$').firstMatch(value.trim());
  if (match == null) return 'Usa el formato MM/AA.';
  final current = now ?? DateTime.now();
  final expiry = DateTime(2000 + int.parse(match[2]!), int.parse(match[1]!));
  final currentMonth = DateTime(current.year, current.month);
  return expiry.isAfter(currentMonth) ? null : 'La tarjeta está vencida.';
}

String? validateCvc(String value) =>
    RegExp(r'^\d{3,4}$').hasMatch(value.trim()) ? null : 'Usa 3 o 4 dígitos.';
