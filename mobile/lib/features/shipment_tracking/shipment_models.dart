class ShipmentState {
  static const pending = 'pendiente';
  static const assigned = 'asignado';
  static const onTheWay = 'en_camino';
  static const delivered = 'entregado';
  static const cancelled = 'cancelado';

  static const all = <String>[
    pending,
    assigned,
    onTheWay,
    delivered,
    cancelled,
  ];

  static bool isTerminal(String state) =>
      state == delivered || state == cancelled;
}

class Shipment {
  const Shipment({
    required this.id,
    required this.state,
    required this.stateLabel,
    required this.active,
    this.address,
    this.latitude,
    this.longitude,
    this.reference,
    this.contactPhone,
    this.distanceKm,
    this.shippingCost,
    this.express = false,
    this.driver,
    this.cancellationReason,
    this.createdAt,
    this.assignedAt,
    this.departedAt,
    this.estimatedAt,
    this.deliveredAt,
    this.origin,
    this.customer,
    this.sale,
    this.items = const [],
    this.payment,
  });

  final int id;
  final String state;
  final String stateLabel;
  final bool active;
  final String? address;
  final double? latitude;
  final double? longitude;
  final String? reference;
  final String? contactPhone;
  final double? distanceKm;
  final double? shippingCost;
  final bool express;
  final String? driver;
  final String? cancellationReason;
  final DateTime? createdAt;
  final DateTime? assignedAt;
  final DateTime? departedAt;
  final DateTime? estimatedAt;
  final DateTime? deliveredAt;
  final ShipmentBranch? origin;
  final ShipmentCustomer? customer;
  final ShipmentSaleSummary? sale;
  final List<ShipmentItem> items;
  final ShipmentPayment? payment;

  bool get isTerminal => ShipmentState.isTerminal(state);

  factory Shipment.fromJson(Map<String, dynamic> json) => Shipment(
    id: _intValue(json['id']),
    state: _stringValue(json['estado']),
    stateLabel: _stringValue(
      json['etiqueta_estado'],
      fallback: _stringValue(json['estado']),
    ),
    active: json['activo'] is bool ? json['activo'] as bool : false,
    address: _nullableString(json['direccion']),
    latitude: _nullableDouble(json['latitud']),
    longitude: _nullableDouble(json['longitud']),
    reference: _nullableString(json['referencia']),
    contactPhone: _nullableString(json['telefono_contacto']),
    distanceKm: _nullableDouble(json['distancia_km']),
    shippingCost: _nullableDouble(json['costo_envio']),
    express: json['express'] is bool ? json['express'] as bool : false,
    driver: _nullableString(json['repartidor']),
    cancellationReason: _nullableString(json['motivo_cancelacion']),
    createdAt: parseShipmentUtc(json['fecha_creacion']),
    assignedAt: parseShipmentUtc(json['fecha_asignacion']),
    departedAt: parseShipmentUtc(json['fecha_salida']),
    estimatedAt: parseShipmentUtc(json['fecha_estimada']),
    deliveredAt: parseShipmentUtc(json['fecha_entrega']),
    origin: ShipmentBranch.fromJson(json['sucursal']),
    customer: ShipmentCustomer.fromJson(json['cliente']),
    sale: ShipmentSaleSummary.fromJson(json['venta']),
    items: _items(json['prendas']),
    payment: ShipmentPayment.fromJson(json['pago']),
  );
}

class ShipmentBranch {
  const ShipmentBranch({
    required this.id,
    required this.name,
    this.address,
    this.phone,
    this.city,
    this.latitude,
    this.longitude,
  });

  final int id;
  final String name;
  final String? address;
  final String? phone;
  final String? city;
  final double? latitude;
  final double? longitude;

  static ShipmentBranch? fromJson(Object? value) {
    if (value is! Map) return null;
    final json = Map<String, dynamic>.from(value);
    return ShipmentBranch(
      id: _intValue(json['id']),
      name: _stringValue(json['nombre']),
      address: _nullableString(json['direccion']),
      phone: _nullableString(json['telefono']),
      city: _nullableString(json['ciudad']),
      latitude: _nullableDouble(json['latitud']),
      longitude: _nullableDouble(json['longitud']),
    );
  }
}

class ShipmentCustomer {
  const ShipmentCustomer({required this.id, this.name, this.email, this.phone});

  final int id;
  final String? name;
  final String? email;
  final String? phone;

  static ShipmentCustomer? fromJson(Object? value) {
    if (value is! Map) return null;
    final json = Map<String, dynamic>.from(value);
    return ShipmentCustomer(
      id: _intValue(json['id']),
      name: _nullableString(json['nombre']),
      email: _nullableString(json['email']),
      phone: _nullableString(json['telefono']),
    );
  }
}

class ShipmentSaleSummary {
  const ShipmentSaleSummary({
    required this.id,
    required this.state,
    required this.channel,
    this.date,
    this.receiptNumber,
    this.subtotal,
    this.discount,
    this.shippingCost,
    this.total,
  });

  final int id;
  final String state;
  final String channel;
  final DateTime? date;
  final String? receiptNumber;
  final double? subtotal;
  final double? discount;
  final double? shippingCost;
  final double? total;

  bool get isPaid => state == 'pagada';

  static ShipmentSaleSummary? fromJson(Object? value) {
    if (value is! Map) return null;
    final json = Map<String, dynamic>.from(value);
    return ShipmentSaleSummary(
      id: _intValue(json['id']),
      state: _stringValue(json['estado']),
      channel: _stringValue(json['canal']),
      date: parseShipmentUtc(json['fecha']),
      receiptNumber: _nullableString(json['nro_comprobante']),
      subtotal: _nullableDouble(json['subtotal']),
      discount: _nullableDouble(json['descuento']),
      shippingCost: _nullableDouble(json['costo_envio']),
      total: _nullableDouble(json['total']),
    );
  }
}

class ShipmentItem {
  const ShipmentItem({
    required this.id,
    required this.sku,
    required this.garment,
    required this.size,
    required this.color,
    required this.quantity,
  });

  final int id;
  final String sku;
  final String garment;
  final String size;
  final String color;
  final int quantity;

  factory ShipmentItem.fromJson(Map<String, dynamic> json) => ShipmentItem(
    id: _intValue(json['id']),
    sku: _stringValue(json['sku']),
    garment: _stringValue(json['prenda']),
    size: _stringValue(json['talla']),
    color: _stringValue(json['color']),
    quantity: _intValue(json['cantidad']),
  );
}

class ShipmentPayment {
  const ShipmentPayment({
    this.method,
    this.gateway,
    this.label,
    this.amount,
    this.externalReference,
    this.date,
    this.status,
  });

  final String? method;
  final String? gateway;
  final String? label;
  final double? amount;
  final String? externalReference;
  final DateTime? date;
  final String? status;

  static ShipmentPayment? fromJson(Object? value) {
    if (value is! Map) return null;
    final json = Map<String, dynamic>.from(value);
    return ShipmentPayment(
      method: _nullableString(json['metodo']),
      gateway: _nullableString(json['pasarela']),
      label: _nullableString(json['etiqueta']),
      amount: _nullableDouble(json['monto']),
      externalReference: _nullableString(json['referencia_externa']),
      date: parseShipmentUtc(json['fecha']),
      status: _nullableString(json['estado']),
    );
  }
}

DateTime? parseShipmentUtc(Object? value) {
  if (value is! String || value.trim().isEmpty) return null;
  final raw = value.trim();
  final hasZone = RegExp(
    r'(z|[+-]\d{2}:\d{2})$',
    caseSensitive: false,
  ).hasMatch(raw);
  final parsed = DateTime.tryParse(hasZone ? raw : '${raw}Z');
  return parsed?.toLocal();
}

String formatShipmentDate(DateTime? value) {
  if (value == null) return 'No informado';
  return '${_twoDigits(value.day)}/${_twoDigits(value.month)}/${value.year} '
      '${_twoDigits(value.hour)}:${_twoDigits(value.minute)}';
}

List<ShipmentItem> _items(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => ShipmentItem.fromJson(Map<String, dynamic>.from(item)))
      .toList(growable: false);
}

int _intValue(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value') ?? 0;
}

double? _nullableDouble(Object? value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse('$value');
}

String _stringValue(Object? value, {String fallback = ''}) =>
    value is String ? value : fallback;

String? _nullableString(Object? value) => value is String ? value : null;

String _twoDigits(int value) => value.toString().padLeft(2, '0');
