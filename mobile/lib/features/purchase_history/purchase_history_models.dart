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
  });

  final int id;
  final int variantId;
  final String sku;
  final String garment;
  final String size;
  final String color;
  final int quantity;
  final double unitPrice;
  final double subtotal;

  factory PurchaseDetail.fromJson(Map<String, dynamic> json) => PurchaseDetail(
    id: _intValue(json['id']),
    variantId: _intValue(json['variante_id']),
    sku: _stringValue(json['sku']),
    garment: _stringValue(json['prenda']),
    size: _stringValue(json['talla']),
    color: _stringValue(json['color']),
    quantity: _intValue(json['cantidad']),
    unitPrice: _doubleValue(json['precio_unitario']),
    subtotal: _doubleValue(json['subtotal']),
  );
}

class PurchasePayment {
  const PurchasePayment({
    required this.id,
    required this.method,
    required this.amount,
    required this.status,
    required this.externalReference,
  });

  final int id;
  final String method;
  final double amount;
  final String status;
  final String? externalReference;

  factory PurchasePayment.fromJson(Map<String, dynamic> json) =>
      PurchasePayment(
        id: _intValue(json['id']),
        method: _stringValue(json['metodo']),
        amount: _doubleValue(json['monto']),
        status: _stringValue(json['estado']),
        externalReference: _nullableString(json['referencia_externa']),
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

String _stringValue(Object? value) => value is String ? value : '';

String? _nullableString(Object? value) => value is String ? value : null;

String _twoDigits(int value) => value.toString().padLeft(2, '0');
