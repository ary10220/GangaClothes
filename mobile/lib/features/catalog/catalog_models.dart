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

/// Recurso del probador virtual registrado por el admin para una variante
/// (`asset_ar`): un PNG con fondo transparente y su escala.
class ArResource {
  const ArResource({
    required this.id,
    required this.type,
    required this.url,
    required this.scale,
  });

  final int id;
  final String type;
  final String url;
  final double scale;

  bool get isPngOverlay => type == 'png_overlay';

  factory ArResource.fromJson(Map<String, dynamic> json) => ArResource(
    id: _requiredInt(json, 'id'),
    type: _nullableString(json['tipo']) ?? 'png_overlay',
    url: _requiredString(json, 'url_recurso'),
    scale: _nullableDouble(json['escala']) ?? 1,
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
    this.hasFittingRoom = false,
    this.arResources = const [],
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
  final bool hasFittingRoom;
  final List<ArResource> arResources;

  /// Último PNG registrado: el backend solo agrega recursos, así que el más
  /// reciente reemplaza a los anteriores.
  ArResource? get pngOverlay {
    for (final resource in arResources.reversed) {
      if (resource.isPngOverlay && resource.url.trim().isNotEmpty) {
        return resource;
      }
    }
    return null;
  }

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
    hasFittingRoom: json['tiene_probador'] == true,
    arResources: json['recursos_ar'] is List
        ? _list(
            json['recursos_ar'],
          ).map(ArResource.fromJson).toList(growable: false)
        : const [],
  );
}

class Product {
  const Product({
    required this.id,
    required this.name,
    required this.description,
    required this.brand,
    required this.salePrice,
    required this.finalPrice,
    this.discount,
    this.promotion,
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
  final double finalPrice;
  final double? discount;
  final CatalogPromotion? promotion;
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
    finalPrice:
        _nullableDouble(json['precio_final']) ??
        _requiredDouble(json, 'precio_venta'),
    discount: _nullableDouble(json['descuento']),
    promotion: CatalogPromotion.fromJson(json['promocion']),
    imageUrl: _nullableString(json['imagen_url']),
    categoryId: _requiredInt(json, 'categoria_id'),
    collectionId: _nullableInt(json['coleccion_id']),
    availableTotal: _requiredInt(json, 'disponible_total'),
    variants: _list(
      json['variantes'],
    ).map(Variant.fromJson).toList(growable: false),
  );
}

class CatalogPromotion {
  const CatalogPromotion({
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

  static CatalogPromotion? fromJson(Object? value) {
    if (value is! Map) return null;
    final json = Map<String, dynamic>.from(value);
    return CatalogPromotion(
      id: _nullableInt(json['id']),
      name: _nullableString(json['nombre']),
      discountType: _nullableString(json['tipo_descuento']),
      value: _nullableDouble(json['valor']),
      label: _nullableString(json['etiqueta']),
      endDate: _nullableString(json['fecha_fin']),
    );
  }
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

double? _nullableDouble(Object? value) {
  if (value is num) return value.toDouble();
  return value is String ? double.tryParse(value) : null;
}

String _requiredString(Map<String, dynamic> json, String key) {
  final value = json[key];
  if (value is! String) throw FormatException('Missing string field: $key');
  return value;
}

String? _nullableString(Object? value) => value is String ? value : null;
