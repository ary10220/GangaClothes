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
    double? finalPrice,
    this.discount,
    this.promotion,
    this.available,
    this.reaches = true,
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
  final CartPromotion? promotion;
  final double subtotal;
  final int? available;
  final bool reaches;

  bool get hasInsufficientStock => reaches == false;
  bool get hasPromotion => promotion != null;

  factory CartLine.fromJson(Map<String, dynamic> json) => CartLine(
    id: _intValue(json['id']),
    variantId: _intValue(json['variante_id']),
    sku: _stringValue(json['sku']),
    garment: _stringValue(json['prenda']),
    size: _stringValue(json['talla']),
    color: _stringValue(json['color']),
    quantity: _intValue(json['cantidad']),
    unitPrice: _doubleValue(json['precio_unitario']),
    finalPrice: _doubleValue(json['precio_final'] ?? json['precio_unitario']),
    discount: _nullableDouble(json['descuento']),
    promotion: _nullablePromotion(json['promocion']),
    subtotal: _doubleValue(json['subtotal']),
    available: _nullableInt(json['disponible']),
    reaches: json['alcanza'] != false,
  );
}

class CartPromotion {
  const CartPromotion({this.id, this.name, this.label});

  final int? id;
  final String? name;
  final String? label;

  String? get displayName => label ?? name;

  factory CartPromotion.fromJson(Map<String, dynamic> json) => CartPromotion(
    id: _nullableInt(json['id']),
    name: _nullableString(json['nombre']),
    label: _nullableString(json['etiqueta']),
  );
}

class CartShipment {
  const CartShipment({
    this.id,
    this.state,
    this.address,
    this.reference,
    this.contactPhone,
    this.latitude,
    this.longitude,
    this.express,
    this.distanceKm,
    this.estimatedAt,
  });

  final int? id;
  final String? state;
  final String? address;
  final String? reference;
  final String? contactPhone;
  final double? latitude;
  final double? longitude;
  final bool? express;
  final double? distanceKm;
  final String? estimatedAt;

  factory CartShipment.fromJson(Map<String, dynamic> json) => CartShipment(
    id: _nullableInt(json['id']),
    state: _nullableString(json['estado']),
    address: _nullableString(json['direccion']),
    reference: _nullableString(json['referencia']),
    contactPhone: _nullableString(json['telefono_contacto']),
    latitude: _nullableDouble(json['latitud']),
    longitude: _nullableDouble(json['longitud']),
    express: json['express'] is bool ? json['express'] as bool : null,
    distanceKm: _nullableDouble(json['distancia_km']),
    estimatedAt: _nullableString(json['fecha_estimada']),
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
    this.deliveryType = 'sucursal',
    this.shippingCost,
    this.shipment,
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
  final String deliveryType;
  final double? shippingCost;
  final CartShipment? shipment;

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
    deliveryType: _stringValue(json['tipo_entrega'], fallback: 'sucursal'),
    shippingCost: _nullableDouble(json['costo_envio']),
    shipment: _nullableShipment(json['envio']),
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

class PaymentMethod {
  const PaymentMethod({
    required this.value,
    required this.label,
    required this.available,
    this.gateway,
    this.detail,
    this.mode,
    this.publicKey,
  });

  final String value;
  final String label;
  final bool available;
  final String? gateway;
  final String? detail;
  final String? mode;
  final String? publicKey;

  factory PaymentMethod.fromJson(Map<String, dynamic> json) => PaymentMethod(
    value: _stringValue(json['valor']),
    label: _stringValue(json['etiqueta']),
    available: json['disponible'] == true,
    gateway: _nullableString(json['pasarela']),
    detail: _nullableString(json['detalle']),
    mode: _nullableString(json['modo']),
    publicKey: _nullableString(json['clave_publica']),
  );
}

enum QrPaymentState { pending, approved, expired, annulled }

class QrPayment {
  const QrPayment({
    required this.saleId,
    required this.qrId,
    required this.state,
    this.paymentId,
    this.description,
    this.imageBase64,
    this.amount,
    this.currency,
    this.expiresAt,
    this.operationNumber,
    this.paymentResult,
  });

  final int saleId;
  final String qrId;
  final QrPaymentState state;
  final int? paymentId;
  final String? description;
  final String? imageBase64;
  final double? amount;
  final String? currency;
  final String? expiresAt;
  final String? operationNumber;
  final PaymentResult? paymentResult;

  bool get isPending => state == QrPaymentState.pending;
  bool get isTerminal => !isPending;

  factory QrPayment.fromJson(Map<String, dynamic> json) {
    final backendState = _stringValue(json['estado']).toUpperCase();
    final state = switch (backendState) {
      'P' || 'U' => QrPaymentState.approved,
      'V' => QrPaymentState.expired,
      'A' => QrPaymentState.annulled,
      _ when json['aprobado'] == true => QrPaymentState.approved,
      _ => QrPaymentState.pending,
    };
    final sale = json['venta'];
    final payment = json['pago'];
    final result = sale is Map && payment is Map
        ? PaymentResult.fromJson(json)
        : null;
    return QrPayment(
      saleId: _intValue(json['venta_id']),
      qrId: _stringValue(json['qr_id']),
      state: state,
      paymentId: _nullableInt(json['pago_id']),
      description: _nullableString(json['descripcion']),
      imageBase64: _nullableString(json['imagen_base64']),
      amount: _nullableDouble(json['monto']),
      currency: _nullableString(json['moneda']),
      expiresAt: _nullableString(json['expira']),
      operationNumber: _nullableString(json['numero_operacion']),
      paymentResult: result,
    );
  }
}

class PaymentResult {
  const PaymentResult({
    required this.approved,
    required this.sale,
    this.reason,
    this.receiptNumber,
    this.externalReference,
    this.paymentLabel,
    this.paymentGateway,
  });

  final bool approved;
  final Cart sale;
  final String? reason;
  final String? receiptNumber;
  final String? externalReference;
  final String? paymentLabel;
  final String? paymentGateway;

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
      paymentLabel: _nullableString(payment['etiqueta']),
      paymentGateway: _nullableString(payment['pasarela']),
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

double? _nullableDouble(Object? value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse('$value');
}

String _stringValue(Object? value, {String fallback = ''}) =>
    value is String ? value : fallback;

String? _nullableString(Object? value) => value is String ? value : null;

CartPromotion? _nullablePromotion(Object? value) {
  if (value is! Map) return null;
  return CartPromotion.fromJson(Map<String, dynamic>.from(value));
}

CartShipment? _nullableShipment(Object? value) {
  if (value is! Map) return null;
  return CartShipment.fromJson(Map<String, dynamic>.from(value));
}
