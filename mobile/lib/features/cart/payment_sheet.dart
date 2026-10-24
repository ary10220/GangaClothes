import 'dart:convert';

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
  String? _selectedMethod;
  bool _attempted = false;

  @override
  void initState() {
    super.initState();
    _number = TextEditingController(text: '4242 4242 4242 4242');
    _holder = TextEditingController(text: widget.initialHolder);
    _expiry = TextEditingController(text: '12/30');
    _selectedMethod =
        widget.controller.availablePaymentMethods.firstOrNull?.value;
    widget.controller.addListener(_onControllerChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onControllerChanged);
    _clearCardFields();
    _number.dispose();
    _holder.dispose();
    _expiry.dispose();
    super.dispose();
  }

  void _clearCardFields() {
    _number.clear();
    _holder.clear();
    _expiry.clear();
  }

  void _onControllerChanged() {
    if (!mounted) return;
    if (widget.controller.receipt != null) {
      Navigator.of(context).pop();
      return;
    }
    final available = widget.controller.availablePaymentMethods;
    if (_selectedMethod == null ||
        !available.any((method) => method.value == _selectedMethod)) {
      _selectedMethod = available.firstOrNull?.value;
    }
    setState(() {});
  }

  PaymentMethod? get _method {
    for (final method in widget.controller.paymentMethods) {
      if (method.value == _selectedMethod) return method;
    }
    return null;
  }

  Future<void> _submit() async {
    final method = _method;
    if (method == null || !method.available) return;
    if (method.value == 'qr') {
      await widget.controller.startQrPayment();
      return;
    }
    setState(() => _attempted = true);
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final cardNumber = _number.text.replaceAll(' ', '');
    try {
      await widget.controller.checkout(cardNumber: cardNumber);
    } finally {
      // The PAN must only exist until the request has been submitted. There is
      // No security-code field or value exists in this flow.
      _clearCardFields();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cart = widget.controller.pendingSale ?? widget.controller.cart;
    if (cart == null) return const SizedBox.shrink();
    final processing = widget.controller.paymentProcessing;
    final qr = widget.controller.qrPayment;
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
              const Text('MÉTODO DE PAGO'),
              const SizedBox(height: 4),
              Text(
                'Pagar Bs ${formatCartMoney(cart.total)}',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              if (widget.controller.paymentMethodsLoading)
                const LinearProgressIndicator(),
              if (widget.controller.paymentMethods.isEmpty &&
                  !widget.controller.paymentMethodsLoading)
                const GcFeedback(
                  message:
                      'No hay métodos de pago disponibles en este momento.',
                  variant: GcFeedbackVariant.error,
                ),
              RadioGroup<String>(
                groupValue: _selectedMethod,
                onChanged: (value) {
                  if (value != null) setState(() => _selectedMethod = value);
                },
                child: Column(
                  children: [
                    for (final method in widget.controller.paymentMethods)
                      _methodTile(method, processing || qr?.isPending == true),
                  ],
                ),
              ),
              if (_method?.value == 'tarjeta') ...[
                const SizedBox(height: 8),
                const Text(
                  'Usá una tarjeta de prueba. El número se envía solo para elegir el token de prueba y se borra al terminar el intento.',
                ),
                const SizedBox(height: 14),
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
                GcField(
                  label: 'Vence (MM/AA)',
                  controller: _expiry,
                  enabled: !processing,
                  keyboardType: TextInputType.datetime,
                  validator: (value) =>
                      _attempted ? validateCardExpiry(value ?? '') : null,
                ),
              ],
              if (_method?.value == 'qr' && qr != null) _buildQr(qr),
              if (widget.controller.paymentError != null) ...[
                const SizedBox(height: 8),
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
                      label: processing
                          ? 'Procesando…'
                          : qr?.isPending == true
                          ? 'Esperando pago…'
                          : _method?.value == 'qr'
                          ? 'Generar QR'
                          : 'Pagar',
                      loading: processing,
                      variant: GcButtonVariant.primary,
                      onPressed:
                          processing || qr?.isPending == true || _method == null
                          ? null
                          : _submit,
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

  Widget _methodTile(PaymentMethod method, bool locked) {
    final details = [
      if (method.gateway?.trim().isNotEmpty == true)
        'Pasarela: ${method.gateway}',
      if (method.mode?.trim().isNotEmpty == true) 'Modo: ${method.mode}',
      if (method.detail?.trim().isNotEmpty == true) method.detail!,
    ].join(' · ');
    return RadioListTile<String>(
      value: method.value,
      dense: true,
      contentPadding: EdgeInsets.zero,
      enabled: method.available && !locked,
      title: Text(method.label),
      subtitle: Text(
        details.isEmpty
            ? (method.available ? 'Disponible' : 'No disponible')
            : details,
      ),
    );
  }

  Widget _buildQr(QrPayment qr) {
    final state = switch (qr.state) {
      QrPaymentState.pending =>
        widget.controller.qrPolling
            ? 'Esperando confirmación del BCP…'
            : 'QR generado',
      QrPaymentState.approved => 'Pago aprobado',
      QrPaymentState.expired => 'QR vencido',
      QrPaymentState.annulled => 'QR anulado',
    };
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(state, style: const TextStyle(fontWeight: FontWeight.w700)),
          if (qr.imageBase64?.isNotEmpty == true) ...[
            const SizedBox(height: 10),
            Center(child: _qrImage(qr.imageBase64!)),
          ],
          if (qr.expiresAt?.isNotEmpty == true)
            Text(
              'Vence: ${qr.expiresAt}',
              style: const TextStyle(fontSize: 12),
            ),
          if (qr.operationNumber?.isNotEmpty == true)
            Text(
              'Operación: ${qr.operationNumber}',
              style: const TextStyle(fontSize: 12),
            ),
        ],
      ),
    );
  }

  Widget _qrImage(String value) {
    try {
      return Image.memory(
        base64Decode(value),
        width: 220,
        height: 220,
        errorBuilder: (_, _, _) => const Text('No se pudo mostrar el QR.'),
      );
    } on FormatException {
      return const Text('No se pudo mostrar el QR.');
    }
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
  final match = RegExp(
    r'^(0[1-9]|1[0-2])/([0-9]{2})$',
  ).firstMatch(value.trim());
  if (match == null) return 'Usa el formato MM/AA.';
  final current = now ?? DateTime.now();
  final expiry = DateTime(2000 + int.parse(match[2]!), int.parse(match[1]!));
  final currentMonth = DateTime(current.year, current.month);
  return expiry.isAfter(currentMonth) ? null : 'La tarjeta está vencida.';
}
