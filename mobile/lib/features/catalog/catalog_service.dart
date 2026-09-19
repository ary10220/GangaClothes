import '../../core/network/api_client.dart';
import 'catalog_models.dart';

class CatalogFilters {
  const CatalogFilters({
    this.search = '',
    this.categoryId,
    this.seasonId,
    this.sizeId,
    this.colorId,
    this.branchId,
  });

  final String search;
  final int? categoryId;
  final int? seasonId;
  final int? sizeId;
  final int? colorId;
  final int? branchId;

  Map<String, dynamic> toQuery() => buildCatalogQuery(
    q: search,
    categoryId: categoryId,
    seasonId: seasonId,
    sizeId: sizeId,
    colorId: colorId,
    branchId: branchId,
  );
}

/// Pure query construction keeps the backend contract independently testable.
Map<String, dynamic> buildCatalogQuery({
  String? q,
  int? categoryId,
  int? seasonId,
  int? sizeId,
  int? colorId,
  int? branchId,
}) {
  final query = <String, dynamic>{};
  final search = q?.trim() ?? '';
  if (search.isNotEmpty) query['q'] = search;
  if (categoryId != null) query['categoria_id'] = categoryId;
  if (seasonId != null) query['temporada_id'] = seasonId;
  if (sizeId != null) query['talla_id'] = sizeId;
  if (colorId != null) query['color_id'] = colorId;
  if (branchId != null) query['sucursal_id'] = branchId;
  return query;
}

abstract interface class CatalogDataSource {
  Future<List<Product>> fetchCatalog(CatalogFilters filters);

  Future<CatalogOptions> fetchOptions();
}

class CatalogService implements CatalogDataSource {
  const CatalogService(this.apiClient);

  final ApiClient apiClient;

  @override
  Future<List<Product>> fetchCatalog(CatalogFilters filters) async {
    final response = await apiClient.request<Object?>(
      '/catalogo',
      queryParameters: filters.toQuery(),
    );
    return _products(response.data);
  }

  @override
  Future<CatalogOptions> fetchOptions() async {
    final responses = await Future.wait([
      apiClient.request<Object?>('/admin/temporadas'),
      apiClient.request<Object?>('/admin/categorias'),
      apiClient.request<Object?>('/admin/tallas'),
      apiClient.request<Object?>('/admin/colores'),
      apiClient.request<Object?>('/admin/sucursales'),
    ]);
    return CatalogOptions(
      seasons: _options(responses[0].data),
      categories: _options(responses[1].data),
      sizes: _options(responses[2].data),
      colors: _options(responses[3].data),
      branches: _branches(responses[4].data),
    );
  }
}

List<Product> _products(Object? data) {
  if (data is! List) {
    throw const FormatException('Catalog response is not a list');
  }
  return data
      .map((item) => Product.fromJson(Map<String, dynamic>.from(item as Map)))
      .toList(growable: false);
}

List<CatalogOption> _options(Object? data) {
  if (data is! List) {
    throw const FormatException('Option response is not a list');
  }
  return data
      .map(
        (item) =>
            CatalogOption.fromJson(Map<String, dynamic>.from(item as Map)),
      )
      .toList(growable: false);
}

List<BranchOption> _branches(Object? data) {
  if (data is! List) {
    throw const FormatException('Branch response is not a list');
  }
  return data
      .map(
        (item) => BranchOption.fromJson(Map<String, dynamic>.from(item as Map)),
      )
      .toList(growable: false);
}
