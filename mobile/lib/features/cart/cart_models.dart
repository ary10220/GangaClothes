class CartLine {
  const CartLine({
    required this.id,
    required this.variantId,
    required this.sku,
    required this.garment,
    required this.size,
    required this.color,
    required this.quantity,
    required this.unitPrice,
    required this.subtotal,
    this.available,
    this.reaches = true,
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
  final int? available;
  final bool reaches;

  bool get hasInsufficientStock => reaches == false;

  factory CartLine.fromJson(Map<String, dynamic> json) => CartLine(
    id: _intValue(json['id']),
    variantId: _intValue(json['variante_id']),
    sku: _stringValue(json['sku']),
    garment: _stringValue(json['prenda']),
    size: _stringValue(json['talla']),
    color: _stringValue(json['color']),
    quantity: _intValue(json['cantidad']),
    unitPrice: _doubleValue(json['precio_unitario']),
    subtotal: _doubleValue(json['subtotal']),
    available: _nullableInt(json['disponible']),
    reaches: json['alcanza'] != false,
  );
}

class Cart {
  const Cart({
    required this.id,
    required this.status,
    required this.branchId,
    required this.branchName,
    required this.units,
    required this.subtotal,
    required this.discount,
    required this.total,
    required this.receiptNumber,
    required this.lines,
  });

  final int id;
  final String status;
  final int branchId;
  final String? branchName;
  final int units;
  final double subtotal;
  final double discount;
  final double total;
  final String? receiptNumber;
  final List<CartLine> lines;

  bool get isEmpty => lines.isEmpty;
  bool get hasInsufficientStock =>
      lines.any((line) => line.hasInsufficientStock);

  factory Cart.fromJson(Map<String, dynamic> json) => Cart(
    id: _intValue(json['id']),
    status: _stringValue(json['estado'], fallback: 'carrito'),
    branchId: _intValue(json['sucursal_id']),
    branchName: _nullableString(json['sucursal']),
    units: _intValue(json['unidades']),
    subtotal: _doubleValue(json['subtotal']),
    discount: _doubleValue(json['descuento']),
    total: _doubleValue(json['total']),
    receiptNumber: _nullableString(json['nro_comprobante']),
    lines: _lines(json['detalle']),
  );
}

class CartBranch {
  const CartBranch({
    required this.id,
    required this.name,
    required this.active,
    this.address,
  });

  final int id;
  final String name;
  final bool active;
  final String? address;

  factory CartBranch.fromJson(Map<String, dynamic> json) => CartBranch(
    id: _intValue(json['id']),
    name: _stringValue(json['nombre']),
    active: json['activo'] != false,
    address: _nullableString(json['direccion']),
  );
}

class PaymentResult {
  const PaymentResult({
    required this.approved,
    required this.sale,
    this.reason,
    this.receiptNumber,
    this.externalReference,
  });

  final bool approved;
  final Cart sale;
  final String? reason;
  final String? receiptNumber;
  final String? externalReference;

  factory PaymentResult.fromJson(Map<String, dynamic> json) {
    final payment = _map(json['pago']);
    final sale = Cart.fromJson(_map(json['venta']));
    return PaymentResult(
      approved: json['aprobado'] == true,
      sale: sale,
      reason: _nullableString(json['motivo']),
      receiptNumber:
          _nullableString(json['nro_comprobante']) ?? sale.receiptNumber,
      externalReference: _nullableString(payment['referencia_externa']),
    );
  }
}

typedef CartPaymentResult = PaymentResult;

String formatCartMoney(Object? value) {
  final number = value is num ? value.toDouble() : double.tryParse('$value');
  if (number == null || !number.isFinite) return '0,00';
  final fixed = number.abs().toStringAsFixed(2).split('.');
  final integer = fixed.first.replaceAllMapped(
    RegExp(r'(?<=\d)(?=(\d{3})+$)'),
    (_) => '.',
  );
  return '${number.isNegative ? '-' : ''}$integer,${fixed.last}';
}

Map<String, dynamic> _map(Object? value) {
  if (value is! Map) throw const FormatException('Expected a JSON object');
  return Map<String, dynamic>.from(value);
}

List<CartLine> _lines(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => CartLine.fromJson(Map<String, dynamic>.from(item)))
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

String _stringValue(Object? value, {String fallback = ''}) =>
    value is String ? value : fallback;

String? _nullableString(Object? value) => value is String ? value : null;
