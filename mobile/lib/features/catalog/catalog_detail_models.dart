import 'catalog_models.dart';

class CatalogColorChoice {
  const CatalogColorChoice({
    required this.id,
    required this.name,
    required this.hex,
  });

  final int id;
  final String name;
  final String? hex;
}

class CatalogSizeChoice {
  const CatalogSizeChoice({required this.id, required this.name});

  final int id;
  final String name;
}

class ReservationRequest {
  const ReservationRequest({
    required this.branchId,
    required this.visitAt,
    required this.variantId,
    required this.quantity,
    this.notes,
  });

  final int branchId;
  final DateTime visitAt;
  final int variantId;
  final int quantity;
  final String? notes;

  Map<String, dynamic> toJson() => {
    'sucursal_id': branchId,
    'fecha_hora_prueba': formatLocalIsoWithoutTimezone(visitAt),
    'notas': notes?.trim().isEmpty == true ? null : notes?.trim(),
    'detalle': [
      {'variante_id': variantId, 'cantidad': quantity},
    ],
  };
}

class ReservationSummary {
  const ReservationSummary({
    required this.id,
    required this.branchId,
    required this.branchName,
    required this.visitAt,
  });

  final int id;
  final int branchId;
  final String? branchName;
  final DateTime? visitAt;

  factory ReservationSummary.fromJson(Map<String, dynamic> json) =>
      ReservationSummary(
        id: _intValue(json['id']),
        branchId: _intValue(json['sucursal_id']),
        branchName: _stringValue(json['sucursal']),
        visitAt: _dateValue(json['fecha_hora_prueba']),
      );
}

class CartLineSummary {
  const CartLineSummary({required this.id, required this.variantId});

  final int id;
  final int variantId;

  factory CartLineSummary.fromJson(Map<String, dynamic> json) =>
      CartLineSummary(
        id: _intValue(json['id']),
        variantId: _intValue(json['variante_id']),
      );
}

class CartSummary {
  const CartSummary({
    required this.id,
    required this.branchId,
    required this.branchName,
    required this.units,
    required this.total,
    required this.detail,
  });

  final int id;
  final int branchId;
  final String? branchName;
  final int units;
  final double total;
  final List<CartLineSummary> detail;

  factory CartSummary.fromJson(Map<String, dynamic> json) => CartSummary(
    id: _intValue(json['id']),
    branchId: _intValue(json['sucursal_id']),
    branchName: _stringValue(json['sucursal']),
    units: _intValue(json['unidades']),
    total: _doubleValue(json['total']),
    detail: _list(
      json['detalle'],
    ).map(CartLineSummary.fromJson).toList(growable: false),
  );
}

String formatLocalIsoWithoutTimezone(DateTime value) {
  final local = value.toLocal();
  return '${local.year.toString().padLeft(4, '0')}-'
      '${local.month.toString().padLeft(2, '0')}-'
      '${local.day.toString().padLeft(2, '0')}T'
      '${local.hour.toString().padLeft(2, '0')}:'
      '${local.minute.toString().padLeft(2, '0')}:'
      '${local.second.toString().padLeft(2, '0')}';
}

int _intValue(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value') ?? 0;
}

double _doubleValue(Object? value) {
  if (value is num) return value.toDouble();
  return double.tryParse('$value') ?? 0;
}

String? _stringValue(Object? value) => value is String ? value : null;

DateTime? _dateValue(Object? value) =>
    value is String ? DateTime.tryParse(value) : null;

List<Map<String, dynamic>> _list(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList(growable: false);
}

List<CatalogColorChoice> colorChoices(Product product) {
  final choices = <int, CatalogColorChoice>{};
  for (final variant in product.variants) {
    choices.putIfAbsent(
      variant.colorId,
      () => CatalogColorChoice(
        id: variant.colorId,
        name: variant.colorName,
        hex: variant.colorHex,
      ),
    );
  }
  return choices.values.toList(growable: false);
}

List<CatalogSizeChoice> sizeChoices(Product product) {
  final choices = <int, CatalogSizeChoice>{};
  for (final variant in product.variants) {
    choices.putIfAbsent(
      variant.sizeId,
      () => CatalogSizeChoice(id: variant.sizeId, name: variant.sizeName),
    );
  }
  return choices.values.toList(growable: false);
}
