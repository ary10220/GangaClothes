/// Typed responses used by the public catalog and its filter resources.
class Availability {
  const Availability({
    required this.branchId,
    required this.branchName,
    required this.available,
  });

  final int branchId;
  final String branchName;
  final int available;

  factory Availability.fromJson(Map<String, dynamic> json) => Availability(
    branchId: _requiredInt(json, 'sucursal_id'),
    branchName: _requiredString(json, 'sucursal'),
    available: _requiredInt(json, 'disponible'),
  );
}

class Variant {
  const Variant({
    required this.id,
    required this.sku,
    required this.sizeId,
    required this.sizeName,
    required this.colorId,
    required this.colorName,
    required this.colorHex,
    required this.imageUrl,
    required this.availableTotal,
    required this.availability,
  });

  final int id;
  final String sku;
  final int sizeId;
  final String sizeName;
  final int colorId;
  final String colorName;
  final String? colorHex;
  final String? imageUrl;
  final int availableTotal;
  final List<Availability> availability;

  factory Variant.fromJson(Map<String, dynamic> json) => Variant(
    id: _requiredInt(json, 'id'),
    sku: _requiredString(json, 'sku'),
    sizeId: _requiredInt(json, 'talla_id'),
    sizeName: _requiredString(json, 'talla'),
    colorId: _requiredInt(json, 'color_id'),
    colorName: _requiredString(json, 'color'),
    colorHex: _nullableString(json['color_hex']),
    imageUrl: _nullableString(json['imagen_url']),
    availableTotal: _requiredInt(json, 'disponible_total'),
    availability: _list(
      json['disponibilidad'],
    ).map(Availability.fromJson).toList(growable: false),
  );
}

class Product {
  const Product({
    required this.id,
    required this.name,
    required this.description,
    required this.brand,
    required this.salePrice,
    required this.imageUrl,
    required this.categoryId,
    required this.collectionId,
    required this.availableTotal,
    required this.variants,
  });

  final int id;
  final String name;
  final String? description;
  final String? brand;
  final double salePrice;
  final String? imageUrl;
  final int categoryId;
  final int? collectionId;
  final int availableTotal;
  final List<Variant> variants;

  factory Product.fromJson(Map<String, dynamic> json) => Product(
    id: _requiredInt(json, 'id'),
    name: _requiredString(json, 'nombre'),
    description: _nullableString(json['descripcion']),
    brand: _nullableString(json['marca']),
    salePrice: _requiredDouble(json, 'precio_venta'),
    imageUrl: _nullableString(json['imagen_url']),
    categoryId: _requiredInt(json, 'categoria_id'),
    collectionId: _nullableInt(json['coleccion_id']),
    availableTotal: _requiredInt(json, 'disponible_total'),
    variants: _list(
      json['variantes'],
    ).map(Variant.fromJson).toList(growable: false),
  );
}

/// A record returned by the existing catalog option endpoints.
class CatalogOption {
  const CatalogOption({
    required this.id,
    required this.displayName,
    required this.active,
    this.colorHex,
    this.order,
  });

  final int id;
  final String displayName;
  final bool active;
  final String? colorHex;
  final int? order;

  factory CatalogOption.fromJson(Map<String, dynamic> json) => CatalogOption(
    id: _requiredInt(json, 'id'),
    displayName: _requiredString(json, 'nombre'),
    active: json['activo'] != false,
    colorHex: _nullableString(json['codigo_hex']),
    order: _nullableInt(json['orden']),
  );
}

/// A branch keeps its inactive state so the UI can validate saved choices.
class BranchOption {
  const BranchOption({
    required this.id,
    required this.displayName,
    required this.active,
    this.cityId,
    this.address,
    this.phone,
    this.schedule,
  });

  final int id;
  final String displayName;
  final bool active;
  final int? cityId;
  final String? address;
  final String? phone;
  final String? schedule;

  factory BranchOption.fromJson(Map<String, dynamic> json) => BranchOption(
    id: _requiredInt(json, 'id'),
    displayName: _requiredString(json, 'nombre'),
    active: json['activo'] != false,
    cityId: _nullableInt(json['ciudad_id']),
    address: _nullableString(json['direccion']),
    phone: _nullableString(json['telefono']),
    schedule: _nullableString(json['horario']),
  );
}

class CatalogOptions {
  const CatalogOptions({
    this.seasons = const [],
    this.categories = const [],
    this.sizes = const [],
    this.colors = const [],
    this.branches = const [],
  });

  final List<CatalogOption> seasons;
  final List<CatalogOption> categories;
  final List<CatalogOption> sizes;
  final List<CatalogOption> colors;
  final List<BranchOption> branches;
}

String formatBolivianos(Object? value) {
  final number = value is num ? value.toDouble() : double.tryParse('$value');
  if (number == null || !number.isFinite) return '0,00';

  final fixed = number.abs().toStringAsFixed(2);
  final parts = fixed.split('.');
  final integer = parts.first.replaceAllMapped(
    RegExp(r'(?<=\d)(?=(\d{3})+$)'),
    (_) => '.',
  );
  return '${number.isNegative ? '-' : ''}$integer,${parts.last}';
}

List<Map<String, dynamic>> _list(Object? value) {
  if (value is! List) throw const FormatException('Expected a JSON list');
  return value
      .map((item) {
        if (item is! Map) throw const FormatException('Expected a JSON object');
        return Map<String, dynamic>.from(item);
      })
      .toList(growable: false);
}

int _requiredInt(Map<String, dynamic> json, String key) {
  final value = _nullableInt(json[key]);
  if (value == null) throw FormatException('Missing integer field: $key');
  return value;
}

int? _nullableInt(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return value is String ? int.tryParse(value) : null;
}

double _requiredDouble(Map<String, dynamic> json, String key) {
  final value = json[key];
  final number = value is num ? value.toDouble() : double.tryParse('$value');
  if (number == null) throw FormatException('Missing number field: $key');
  return number;
}

String _requiredString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String) throw FormatException('Missing string field: $key');
  return value;
}

String? _nullableString(Object? value) => value is String ? value : null;
