import '../cart/cart_models.dart';

class DeliveryPoint {
  const DeliveryPoint({
    this.id,
    this.name,
    this.address,
    this.city,
    this.latitude,
    this.longitude,
  });

  final int? id;
  final String? name;
  final String? address;
  final String? city;
  final double? latitude;
  final double? longitude;

  factory DeliveryPoint.fromJson(Map<String, dynamic> json) => DeliveryPoint(
    id: _nullableInt(json['id']),
    name: _nullableString(json['nombre'] ?? json['name']),
    address: _nullableString(json['direccion'] ?? json['address']),
    city: _nullableString(json['ciudad'] ?? json['city']),
    latitude: _nullableDouble(json['latitud'] ?? json['latitude']),
    longitude: _nullableDouble(json['longitud'] ?? json['longitude']),
  );
}

class DeliveryBreakdownLine {
  const DeliveryBreakdownLine({
    required this.concept,
    required this.detail,
    required this.amount,
  });

  final String concept;
  final String? detail;
  final double amount;

  bool get isCredit => amount < 0;

  factory DeliveryBreakdownLine.fromJson(Map<String, dynamic> json) =>
      DeliveryBreakdownLine(
        concept: _stringValue(json['concepto'] ?? json['concept']),
        detail: _nullableString(json['detalle'] ?? json['detail']),
        amount: _doubleValue(json['importe'] ?? json['amount']),
      );
}

class DeliveryTariff {
  const DeliveryTariff({
    this.baseCost,
    this.costPerKilometer,
    this.expressSurchargePercentage,
    this.freeShippingFrom,
    this.coverageKilometers,
    this.preparationMinutes,
    this.expressPreparationMinutes,
    this.speedKilometersPerHour,
  });

  final double? baseCost;
  final double? costPerKilometer;
  final double? expressSurchargePercentage;
  final double? freeShippingFrom;
  final double? coverageKilometers;
  final int? preparationMinutes;
  final int? expressPreparationMinutes;
  final double? speedKilometersPerHour;

  factory DeliveryTariff.fromJson(Map<String, dynamic> json) => DeliveryTariff(
    baseCost: _nullableDouble(json['costo_base']),
    costPerKilometer: _nullableDouble(json['costo_por_km']),
    expressSurchargePercentage: _nullableDouble(
      json['recargo_express_porcentaje'],
    ),
    freeShippingFrom: _nullableDouble(json['envio_gratis_desde']),
    coverageKilometers: _nullableDouble(json['cobertura_km']),
    preparationMinutes: _nullableInt(json['minutos_preparacion']),
    expressPreparationMinutes: _nullableInt(
      json['minutos_preparacion_express'],
    ),
    speedKilometersPerHour: _nullableDouble(json['velocidad_kmh']),
  );
}

class DeliveryQuoteInput {
  const DeliveryQuoteInput({
    required this.branchId,
    required this.latitude,
    required this.longitude,
    required this.express,
  });

  final int branchId;
  final double latitude;
  final double longitude;
  final bool express;

  Map<String, dynamic> toJson() => {
    'sucursal_id': branchId,
    'latitud': latitude,
    'longitud': longitude,
    'express': express,
  };

  bool matches(DeliveryQuoteInput other) =>
      branchId == other.branchId &&
      latitude == other.latitude &&
      longitude == other.longitude &&
      express == other.express;
}

class DeliveryInput {
  const DeliveryInput({
    required this.saleId,
    required this.address,
    required this.contactPhone,
    required this.latitude,
    required this.longitude,
    required this.express,
    this.reference,
  });

  final int saleId;
  final String address;
  final String? reference;
  final String contactPhone;
  final double latitude;
  final double longitude;
  final bool express;

  Map<String, dynamic> toJson() {
    final data = <String, dynamic>{
      'venta_id': saleId,
      'direccion': address,
      'telefono_contacto': contactPhone,
      'latitud': latitude,
      'longitud': longitude,
      'express': express,
    };
    final normalizedReference = reference?.trim();
    if (normalizedReference != null && normalizedReference.isNotEmpty) {
      data['referencia'] = normalizedReference;
    }
    return data;
  }
}

class DeliveryQuote {
  const DeliveryQuote({
    required this.withinCoverage,
    required this.coverageMessage,
    required this.breakdown,
    required this.shippingCost,
    required this.distanceKm,
    required this.estimatedMinutes,
    required this.estimatedAt,
    required this.origin,
    required this.destination,
    required this.totalToPay,
    required this.express,
    this.coverageKm,
    this.freeShipping,
    this.freeShippingFrom,
  });

  final bool withinCoverage;
  final String? coverageMessage;
  final List<DeliveryBreakdownLine> breakdown;
  final double? shippingCost;
  final double? distanceKm;
  final int? estimatedMinutes;
  final String? estimatedAt;
  final DeliveryPoint? origin;
  final DeliveryPoint? destination;
  final double? totalToPay;
  final bool express;
  final double? coverageKm;
  final bool? freeShipping;
  final double? freeShippingFrom;

  bool get isComplete =>
      withinCoverage &&
      shippingCost != null &&
      distanceKm != null &&
      estimatedMinutes != null &&
      estimatedAt != null &&
      origin != null &&
      destination != null &&
      totalToPay != null;

  factory DeliveryQuote.fromJson(Map<String, dynamic> json) => DeliveryQuote(
    withinCoverage: json['dentro_de_cobertura'] == true,
    coverageMessage: _nullableString(json['mensaje_cobertura']),
    breakdown: _breakdown(json['desglose']),
    shippingCost: _nullableDouble(json['costo_envio']),
    distanceKm: _nullableDouble(json['distancia_km']),
    estimatedMinutes: _nullableInt(json['minutos_estimados']),
    estimatedAt: _nullableString(json['entrega_estimada']),
    origin: _nullablePoint(json['sucursal']),
    destination: _nullablePoint(json['destino']),
    totalToPay: _nullableDouble(json['total_a_pagar']),
    express: json['express'] == true,
    coverageKm: _nullableDouble(json['cobertura_km']),
    freeShipping: json['gratis'] is bool ? json['gratis'] as bool : null,
    freeShippingFrom: _nullableDouble(json['envio_gratis_desde']),
  );
}

class DeliveryShipment {
  const DeliveryShipment({
    this.id,
    this.state,
    this.address,
    this.reference,
    this.contactPhone,
    this.latitude,
    this.longitude,
    this.express,
    this.distanceKm,
    this.shippingCost,
    this.estimatedAt,
    this.origin,
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
  final double? shippingCost;
  final String? estimatedAt;
  final DeliveryPoint? origin;

  factory DeliveryShipment.fromJson(Map<String, dynamic> json) =>
      DeliveryShipment(
        id: _nullableInt(json['id']),
        state: _nullableString(json['estado']),
        address: _nullableString(json['direccion']),
        reference: _nullableString(json['referencia']),
        contactPhone: _nullableString(json['telefono_contacto']),
        latitude: _nullableDouble(json['latitud']),
        longitude: _nullableDouble(json['longitud']),
        express: json['express'] is bool ? json['express'] as bool : null,
        distanceKm: _nullableDouble(json['distancia_km']),
        shippingCost: _nullableDouble(json['costo_envio']),
        estimatedAt: _nullableString(json['fecha_estimada']),
        origin: _nullablePoint(json['sucursal']),
      );
}

class DeliveryResponse {
  const DeliveryResponse({
    required this.sale,
    required this.quote,
    this.shipment,
  });

  final Cart sale;
  final DeliveryQuote quote;
  final DeliveryShipment? shipment;

  factory DeliveryResponse.fromJson(Map<String, dynamic> json) {
    final shipment = json['envio'];
    final quote = json['cotizacion'];
    return DeliveryResponse(
      sale: Cart.fromJson(_map(json['venta'])),
      quote: DeliveryQuote.fromJson(_map(quote)),
      shipment: shipment is Map
          ? DeliveryShipment.fromJson(Map<String, dynamic>.from(shipment))
          : null,
    );
  }
}

List<DeliveryBreakdownLine> _breakdown(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map(
        (item) =>
            DeliveryBreakdownLine.fromJson(Map<String, dynamic>.from(item)),
      )
      .toList(growable: false);
}

DeliveryPoint? _nullablePoint(Object? value) {
  if (value is! Map) return null;
  return DeliveryPoint.fromJson(Map<String, dynamic>.from(value));
}

Map<String, dynamic> _map(Object? value) {
  if (value is! Map) throw const FormatException('Expected a JSON object');
  return Map<String, dynamic>.from(value);
}

String _stringValue(Object? value) => value is String ? value : '';

String? _nullableString(Object? value) => value is String ? value : null;

int? _nullableInt(Object? value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value');
}

double? _nullableDouble(Object? value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse('$value');
}

double _doubleValue(Object? value) => _nullableDouble(value) ?? 0;
