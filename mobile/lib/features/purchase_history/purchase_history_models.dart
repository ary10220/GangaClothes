class PurchaseDetail {
  const PurchaseDetail({
    required this.id,
    required this.variantId,
    required this.sku,
    required this.garment,
    required this.size,
    required this.color,
    required this.quantity,
    required this.unitPrice,
    required this.subtotal,
    double? finalPrice,
    this.discount,
    this.promotion,
  }) : finalPrice = finalPrice ?? unitPrice;

  final int id;
  final int variantId;
  final String sku;
  final String garment;
  final String size;
  final String color;
  final int quantity;
  final double unitPrice;
  final double finalPrice;
  final double? discount;
  final PurchasePromotion? promotion;
  final double subtotal;

  factory PurchaseDetail.fromJson(Map<String, dynamic> json) => PurchaseDetail(
    id: _intValue(json['id']),
    variantId: _intValue(json['variante_id']),
    sku: _stringValue(json['sku']),
    garment: _stringValue(json['prenda'] ?? json['descripcion']),
    size: _stringValue(json['talla']),
    color: _stringValue(json['color']),
    quantity: _intValue(json['cantidad']),
    unitPrice: _doubleValue(json['precio_unitario']),
    finalPrice: _doubleValue(json['precio_final'] ?? json['precio_unitario']),
    discount: _nullableDouble(json['descuento']),
    promotion: PurchasePromotion.fromJson(json['promocion']),
    subtotal: _doubleValue(json['subtotal']),
  );
}

class PurchasePromotion {
  const PurchasePromotion({
    this.id,
    this.name,
    this.discountType,
    this.value,
    this.label,
    this.endDate,
  });

  final int? id;
  final String? name;
  final String? discountType;
  final double? value;
  final String? label;
  final String? endDate;

  String? get displayName => label ?? name;

  static PurchasePromotion? fromJson(Object? value) {
    if (value is! Map) return null;
    final json = Map<String, dynamic>.from(value);
    return PurchasePromotion(
      id: _nullableInt(json['id']),
      name: _nullableString(json['nombre']),
      discountType: _nullableString(json['tipo_descuento']),
      value: _nullableDouble(json['valor']),
      label: _nullableString(json['etiqueta']),
      endDate: _nullableString(json['fecha_fin']),
    );
  }
}

class PurchasePayment {
  const PurchasePayment({
    required this.id,
    required this.method,
    required this.amount,
    required this.status,
    required this.externalReference,
    this.gateway,
    this.label,
    this.currency,
    this.dateRaw,
  });

  final int id;
  final String method;
  final double amount;
  final String status;
  final String? externalReference;
  final String? gateway;
  final String? label;
  final String? currency;
  final String? dateRaw;

  factory PurchasePayment.fromJson(Map<String, dynamic> json) =>
      PurchasePayment(
        id: _intValue(json['id']),
        method: _stringValue(json['metodo']),
        amount: _doubleValue(json['monto']),
        status: _stringValue(json['estado']),
        externalReference: _nullableString(json['referencia_externa']),
        gateway: _nullableString(json['pasarela']),
        label: _nullableString(json['etiqueta']),
        currency: _nullableString(json['moneda']),
        dateRaw: _nullableString(json['fecha']),
      );
}

class PurchaseShipment {
  const PurchaseShipment({
    required this.id,
    required this.status,
    required this.address,
    required this.total,
    required this.receiptNumber,
    this.reference,
    required this.details,
    required this.payments,
  });

  final int id;
  final String? status;
  final String? address;
  final double total;
  final String? receiptNumber;
  final String? reference;
  final List<PurchaseDetail> details;
  final List<PurchasePayment> payments;

  factory PurchaseShipment.fromJson(Map<String, dynamic> json) =>
      PurchaseShipment(
        id: _intValue(json['id']),
        status: _nullableString(json['estado']),
        address: _nullableString(json['direccion']),
        total: _doubleValue(json['total']),
        receiptNumber: _nullableString(json['nro_comprobante']),
        reference: _nullableString(json['referencia']),
        details: _details(json['detalle']),
        payments: _payments(json['pagos']),
      );
}

class PurchaseReceiptDelivery {
  const PurchaseReceiptDelivery({
    this.type,
    this.address,
    this.branch,
    this.status,
  });

  final String? type;
  final String? address;
  final String? branch;
  final String? status;

  String get displayType => switch (type) {
    'delivery' => 'Delivery',
    'sucursal' => 'Retiro en sucursal',
    _ => type?.trim().isNotEmpty == true ? type! : 'No informado',
  };

  static PurchaseReceiptDelivery? fromJson(Object? value) {
    if (value is String) return PurchaseReceiptDelivery(type: value);
    if (value is! Map) return null;
    final json = Map<String, dynamic>.from(value);
    return PurchaseReceiptDelivery(
      type: _nullableString(json['tipo_entrega'] ?? json['tipo']),
      address: _nullableString(json['direccion']),
      branch: _nullableString(json['sucursal']),
      status: _nullableString(json['estado']),
    );
  }
}

class PurchaseReceipt {
  const PurchaseReceipt({
    required this.receiptNumber,
    required this.dateRaw,
    required this.items,
    required this.subtotal,
    required this.discount,
    required this.shippingCost,
    required this.delivery,
    required this.total,
    required this.currency,
    required this.payment,
  });

  final String? receiptNumber;
  final String? dateRaw;
  final List<PurchaseDetail> items;
  final double subtotal;
  final double discount;
  final double shippingCost;
  final PurchaseReceiptDelivery? delivery;
  final double total;
  final String? currency;
  final PurchasePayment? payment;

  factory PurchaseReceipt.fromJson(Map<String, dynamic> json) =>
      PurchaseReceipt(
        receiptNumber: _nullableString(
          json['nro_comprobante'] ?? json['numero_comprobante'],
        ),
        dateRaw: _nullableString(json['fecha'] ?? json['fecha_emision']),
        items: _details(json['items'] ?? json['detalle']),
        subtotal: _doubleValue(json['subtotal']),
        discount: _doubleValue(json['descuento']),
        shippingCost: _doubleValue(json['costo_envio'] ?? json['envio']),
        delivery: PurchaseReceiptDelivery.fromJson(json['entrega']),
        total: _doubleValue(json['total']),
        currency: _nullableString(json['moneda']),
        payment: _payment(json['pago']),
      );
}

class PurchaseParty {
  const PurchaseParty({required this.id, this.name, this.email});

  final int id;
  final String? name;
  final String? email;

  factory PurchaseParty.fromJson(Map<String, dynamic> json) => PurchaseParty(
    id: _intValue(json['id']),
    name: _nullableString(json['nombre']),
    email: _nullableString(json['email']),
  );
}

class Purchase {
  const Purchase({
    required this.id,
    required this.status,
    required this.channel,
    required this.dateRaw,
    required this.branchId,
    required this.branchName,
    required this.customer,
    required this.cashier,
    required this.reservationId,
    required this.units,
    required this.subtotal,
    required this.discount,
    required this.total,
    required this.receiptNumber,
    required this.details,
    required this.payments,
    this.deliveryType = 'sucursal',
    this.shippingCost,
    this.shipment,
  });

  final int id;
  final String status;
  final String channel;
  final String? dateRaw;
  final int branchId;
  final String? branchName;
  final PurchaseParty? customer;
  final PurchaseParty? cashier;
  final int? reservationId;
  final int units;
  final double subtotal;
  final double discount;
  final double total;
  final String? receiptNumber;
  final List<PurchaseDetail> details;
  final List<PurchasePayment> payments;
  final String deliveryType;
  final double? shippingCost;
  final PurchaseShipment? shipment;

  String get displayReceiptNumber =>
      receiptNumber?.trim().isNotEmpty == true ? receiptNumber! : '#V-$id';

  bool get isDelivery => deliveryType == 'delivery';

  bool get canTrackShipment =>
      status == 'pagada' &&
      isDelivery &&
      shipment != null &&
      shipment!.id > 0 &&
      successfulPayment?.status == 'exitoso';

  factory Purchase.fromJson(Map<String, dynamic> json) => Purchase(
    id: _intValue(json['id']),
    status: _stringValue(json['estado']),
    channel: _stringValue(json['canal']),
    dateRaw: _nullableString(json['fecha']),
    branchId: _intValue(json['sucursal_id']),
    branchName: _nullableString(json['sucursal']),
    customer: _party(json['cliente']),
    cashier: _party(json['cajero']),
    reservationId: _nullableInt(json['reserva_id']),
    units: _intValue(json['unidades']),
    subtotal: _doubleValue(json['subtotal']),
    discount: _doubleValue(json['descuento']),
    total: _doubleValue(json['total']),
    receiptNumber: _nullableString(json['nro_comprobante']),
    details: _details(json['detalle']),
    payments: _payments(json['pagos']),
    deliveryType: _stringValue(json['tipo_entrega'], fallback: 'sucursal'),
    shippingCost: _nullableDouble(json['costo_envio']),
    shipment: _shipment(json['envio']),
  );

  PurchasePayment? get successfulPayment {
    for (final payment in payments.reversed) {
      if (payment.status == 'exitoso') return payment;
    }
    return payments.lastOrNull;
  }
}

DateTime? parsePurchaseTimestamp(String? value) {
  if (value == null || value.trim().isEmpty) return null;
  final hasZone = RegExp(
    r'(z|[+-]\d{2}:\d{2})$',
    caseSensitive: false,
  ).hasMatch(value);
  final parsed = DateTime.tryParse(hasZone ? value : '${value}Z');
  return parsed?.toLocal();
}

String formatPurchaseDate(String? value) {
  final date = parsePurchaseTimestamp(value);
  if (date == null) return value?.trim().isNotEmpty == true ? value! : '—';
  return '${_twoDigits(date.day)}/${_twoDigits(date.month)}/${date.year} '
      '${_twoDigits(date.hour)}:${_twoDigits(date.minute)}';
}

String formatPurchaseMoney(Object? value) {
  final number = value is num ? value.toDouble() : double.tryParse('$value');
  if (number == null || !number.isFinite) return '0,00';
  final fixed = number.abs().toStringAsFixed(2).split('.');
  final integer = fixed.first.replaceAllMapped(
    RegExp(r'(?<=\d)(?=(\d{3})+$)'),
    (_) => '.',
  );
  return '${number.isNegative ? '-' : ''}$integer,${fixed.last}';
}

String purchasePaymentMethod(String? method) => switch (method) {
  'pasarela' => 'Tarjeta / pasarela',
  'efectivo' => 'Efectivo',
  'tarjeta' => 'Tarjeta',
  'qr' => 'QR',
  _ => method?.trim().isNotEmpty == true ? method! : 'No informado',
};

String purchasePaymentStatus(String? status) => status == 'exitoso'
    ? 'aprobado'
    : status?.trim().isNotEmpty == true
    ? status!
    : 'No informado';

PurchaseParty? _party(Object? value) {
  if (value is! Map) return null;
  return PurchaseParty.fromJson(Map<String, dynamic>.from(value));
}

List<PurchaseDetail> _details(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => PurchaseDetail.fromJson(Map<String, dynamic>.from(item)))
      .toList(growable: false);
}

List<PurchasePayment> _payments(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => PurchasePayment.fromJson(Map<String, dynamic>.from(item)))
      .toList(growable: false);
}

int _intValue(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value') ?? 0;
}

int? _nullableInt(Object? value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value');
}

double _doubleValue(Object? value) {
  if (value is num) return value.toDouble();
  return double.tryParse('$value') ?? 0;
}

double? _nullableDouble(Object? value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse('$value');
}

String _stringValue(Object? value, {String fallback = ''}) =>
    value is String ? value : fallback;

String? _nullableString(Object? value) => value is String ? value : null;

PurchaseShipment? _shipment(Object? value) {
  if (value is! Map) return null;
  return PurchaseShipment.fromJson(Map<String, dynamic>.from(value));
}

PurchasePayment? _payment(Object? value) {
  if (value is Map) {
    return PurchasePayment.fromJson(Map<String, dynamic>.from(value));
  }
  if (value is List) {
    for (final item in value) {
      if (item is Map) {
        return PurchasePayment.fromJson(Map<String, dynamic>.from(item));
      }
    }
  }
  return null;
}

String _twoDigits(int value) => value.toString().padLeft(2, '0');
