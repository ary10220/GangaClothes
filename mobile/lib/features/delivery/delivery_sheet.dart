import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_field.dart';
import '../cart/cart_controller.dart';
import '../cart/cart_models.dart';
import 'delivery_models.dart';

class DeliverySheet extends StatefulWidget {
  const DeliverySheet({
    required this.controller,
    this.initialPhone = '',
    super.key,
  });

  final CartController controller;
  final String initialPhone;

  @override
  State<DeliverySheet> createState() => _DeliverySheetState();
}

class _DeliverySheetState extends State<DeliverySheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _address;
  late final TextEditingController _reference;
  late final TextEditingController _phone;
  late final TextEditingController _latitude;
  late final TextEditingController _longitude;
  bool _deliverySelected = false;
  bool _attempted = false;

  CartShipment? get _shipment => widget.controller.cart?.shipment;

  @override
  void initState() {
    super.initState();
    final shipment = _shipment;
    _deliverySelected = widget.controller.hasDelivery;
    _address = TextEditingController(text: shipment?.address ?? '');
    _reference = TextEditingController(text: shipment?.reference ?? '');
    _phone = TextEditingController(
      text: shipment?.contactPhone ?? widget.initialPhone,
    );
    _latitude = TextEditingController(
      text: shipment?.latitude?.toString() ?? '',
    );
    _longitude = TextEditingController(
      text: shipment?.longitude?.toString() ?? '',
    );
    _expressValue = shipment?.express == true;
    widget.controller.beginDeliveryEditing(notify: false);
    widget.controller.addListener(_onControllerChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onControllerChanged);
    widget.controller.endDeliveryEditing();
    _address.dispose();
    _reference.dispose();
    _phone.dispose();
    _latitude.dispose();
    _longitude.dispose();
    super.dispose();
  }

  void _onControllerChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _selectPickup() async {
    if (!_deliverySelected) return;
    if (!widget.controller.hasDelivery) {
      setState(() => _deliverySelected = false);
      return;
    }
    final removed = await widget.controller.removeDelivery();
    if (mounted && removed) setState(() => _deliverySelected = false);
  }

  void _selectDelivery() {
    if (widget.controller.paymentProcessing ||
        widget.controller.pendingSale != null) {
      return;
    }
    setState(() => _deliverySelected = true);
  }

  DeliveryInput? _readInput() {
    if (!(_formKey.currentState?.validate() ?? false)) return null;
    final latitude = double.tryParse(_latitude.text.trim());
    final longitude = double.tryParse(_longitude.text.trim());
    if (latitude == null || longitude == null) return null;
    return DeliveryInput(
      saleId: widget.controller.cart!.id,
      address: _address.text.trim(),
      reference: _reference.text,
      contactPhone: _phone.text.trim(),
      latitude: latitude,
      longitude: longitude,
      express: _expressValue,
    );
  }

  bool _expressValue = false;

  void _setExpress(bool value) {
    setState(() {
      _expressValue = value;
    });
  }

  DeliveryInput? get _currentInput {
    final latitude = double.tryParse(_latitude.text.trim());
    final longitude = double.tryParse(_longitude.text.trim());
    if (latitude == null || longitude == null) return null;
    return DeliveryInput(
      saleId: widget.controller.cart?.id ?? 0,
      address: _address.text.trim(),
      reference: _reference.text,
      contactPhone: _phone.text.trim(),
      latitude: latitude,
      longitude: longitude,
      express: _expressValue,
    );
  }

  DeliveryQuoteInput? get _quoteInput {
    final input = _currentInput;
    if (input == null || widget.controller.cart == null) return null;
    return DeliveryQuoteInput(
      branchId: widget.controller.cart!.branchId,
      latitude: input.latitude,
      longitude: input.longitude,
      express: input.express,
    );
  }

  Future<void> _quote() async {
    setState(() => _attempted = true);
    final input = _readInput();
    final quoteInput = _quoteInput;
    if (input == null || quoteInput == null) return;
    await widget.controller.quoteDelivery(quoteInput);
  }

  Future<void> _save() async {
    setState(() => _attempted = true);
    final input = _readInput();
    final quoteInput = _quoteInput;
    if (input == null || quoteInput == null) return;
    if (!widget.controller.isDeliveryQuoteReady(quoteInput)) return;
    final saved = await widget.controller.createDelivery(input);
    if (mounted && saved) Navigator.of(context).pop();
  }

  String? _requiredText(String? value, {required String label, int min = 1}) {
    if ((value ?? '').trim().length < min) return '$label es obligatorio.';
    return null;
  }

  String? _coordinate(String? value, {required bool latitude}) {
    final parsed = double.tryParse((value ?? '').trim());
    if (parsed == null || !parsed.isFinite) {
      return 'Ingresa una coordenada válida.';
    }
    final valid = latitude
        ? parsed >= -90 && parsed <= 90
        : parsed >= -180 && parsed <= 180;
    return valid ? null : 'La coordenada está fuera de rango.';
  }

  @override
  Widget build(BuildContext context) {
    final quote = widget.controller.deliveryQuote;
    final quoteInput = _quoteInput;
    final quoteReady =
        quoteInput != null &&
        widget.controller.isDeliveryQuoteReady(quoteInput);
    final busy =
        widget.controller.deliveryLoading || widget.controller.deliverySaving;
    return Material(
      color: GangaColors.white,
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 28),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('ENTREGA', style: GangaTextStyles.eyebrow),
                const SizedBox(height: 4),
                const Text(
                  '¿Cómo deseas recibir tu compra?',
                  style: GangaTextStyles.heading,
                ),
                const SizedBox(height: 12),
                RadioGroup<bool>(
                  groupValue: _deliverySelected,
                  onChanged: (value) {
                    if (busy) return;
                    if (value == true) {
                      _selectDelivery();
                    } else {
                      _selectPickup();
                    }
                  },
                  child: Column(
                    children: [
                      RadioListTile<bool>(
                        value: false,
                        title: const Text('Retiro en sucursal'),
                        subtitle: const Text(
                          'Retira tu compra en la sucursal elegida.',
                        ),
                        contentPadding: EdgeInsets.zero,
                      ),
                      RadioListTile<bool>(
                        value: true,
                        title: const Text('Entrega a domicilio'),
                        subtitle: const Text(
                          'El backend cotiza el costo y el tiempo.',
                        ),
                        contentPadding: EdgeInsets.zero,
                      ),
                    ],
                  ),
                ),
                if (!_deliverySelected) ...[
                  const SizedBox(height: 8),
                  const GcFeedback(
                    message:
                        'Tu compra se entregará para retiro en la sucursal elegida.',
                  ),
                ],
                if (_deliverySelected) ...[
                  const SizedBox(height: 8),
                  const GcFeedback(
                    message:
                        'No hay mapa ni permisos de ubicación instalados. Ingresa las coordenadas explícitamente; la app no hace geocodificación ni cálculo de rutas.',
                  ),
                  const SizedBox(height: 14),
                  GcField(
                    label: 'Dirección',
                    controller: _address,
                    enabled: !busy,
                    maxLines: 2,
                    validator: (value) => _attempted
                        ? _requiredText(value, label: 'La dirección', min: 5)
                        : null,
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  GcField(
                    label: 'Referencia (opcional)',
                    controller: _reference,
                    enabled: !busy,
                    maxLines: 2,
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  GcField(
                    label: 'Teléfono de contacto',
                    controller: _phone,
                    enabled: !busy,
                    keyboardType: TextInputType.phone,
                    validator: (value) => _attempted
                        ? _requiredText(value, label: 'El teléfono', min: 6)
                        : null,
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: GcField(
                          label: 'Latitud',
                          controller: _latitude,
                          enabled: !busy,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          validator: (value) => _attempted
                              ? _coordinate(value, latitude: true)
                              : null,
                          onChanged: (_) => setState(() {}),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: GcField(
                          label: 'Longitud',
                          controller: _longitude,
                          enabled: !busy,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          validator: (value) => _attempted
                              ? _coordinate(value, latitude: false)
                              : null,
                          onChanged: (_) => setState(() {}),
                        ),
                      ),
                    ],
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Entrega express'),
                    subtitle: const Text(
                      'El backend aplicará el recargo y el tiempo correspondiente.',
                    ),
                    value: _expressValue,
                    onChanged: busy ? null : _setExpress,
                  ),
                  const SizedBox(height: 4),
                  if (widget.controller.deliveryError != null) ...[
                    GcFeedback(
                      message: widget.controller.deliveryError!.message,
                      variant: GcFeedbackVariant.error,
                    ),
                    const SizedBox(height: 8),
                  ],
                  if (quote != null) _buildQuote(quote),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: GcButton(
                          label: quoteReady
                              ? 'Guardar entrega'
                              : 'Cotizar entrega',
                          loading: busy,
                          onPressed: busy
                              ? null
                              : (quoteReady ? _save : _quote),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: GcButton(
                          label: 'Cancelar',
                          variant: GcButtonVariant.outlined,
                          onPressed: busy
                              ? null
                              : () => Navigator.of(context).pop(),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildQuote(DeliveryQuote quote) {
    if (!quote.withinCoverage) {
      return GcFeedback(
        message:
            quote.coverageMessage ?? 'La dirección está fuera de cobertura.',
        variant: GcFeedbackVariant.error,
      );
    }
    if (!quote.isComplete) {
      return const GcFeedback(
        message:
            'La cotización del backend está incompleta. Vuelve a intentarlo.',
        variant: GcFeedbackVariant.error,
      );
    }
    final origin = quote.origin;
    final destination = quote.destination;
    return Card(
      color: GangaColors.soft,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'COTIZACIÓN DEL BACKEND',
              style: GangaTextStyles.eyebrow,
            ),
            const SizedBox(height: 8),
            if (quote.coverageMessage?.isNotEmpty == true)
              Text(quote.coverageMessage!, style: GangaTextStyles.metadata),
            if (origin != null)
              Text(
                'Origen: ${origin.name ?? 'Sucursal'} · ${_coordinates(origin.latitude, origin.longitude)}',
                style: GangaTextStyles.metadata,
              ),
            if (destination != null)
              Text(
                'Destino: ${_coordinates(destination.latitude, destination.longitude)}',
                style: GangaTextStyles.metadata,
              ),
            if (quote.distanceKm != null)
              Text(
                'Distancia: ${quote.distanceKm} km',
                style: GangaTextStyles.metadata,
              ),
            if (quote.estimatedMinutes != null)
              Text(
                'Tiempo estimado: ${quote.estimatedMinutes} min${quote.estimatedAt == null ? '' : ' · ${quote.estimatedAt}'}',
                style: GangaTextStyles.metadata,
              ),
            const Divider(height: 20),
            for (final line in quote.breakdown) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: Text(line.concept)),
                  Text(
                    'Bs ${formatCartMoney(line.amount)}',
                    style: TextStyle(
                      color: line.isCredit ? GangaColors.success : null,
                      fontWeight: line.isCredit ? FontWeight.w700 : null,
                    ),
                  ),
                ],
              ),
              if (line.detail?.isNotEmpty == true)
                Text(line.detail!, style: GangaTextStyles.metadata),
              const SizedBox(height: 6),
            ],
            if (quote.shippingCost != null)
              Text(
                'Envío según backend: Bs ${formatCartMoney(quote.shippingCost)}',
              ),
            if (quote.totalToPay != null)
              Text(
                'Total a pagar según backend: Bs ${formatCartMoney(quote.totalToPay)}',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
          ],
        ),
      ),
    );
  }

  String _coordinates(double? latitude, double? longitude) {
    if (latitude == null || longitude == null) return 'Sin coordenadas';
    return '$latitude, $longitude';
  }
}
