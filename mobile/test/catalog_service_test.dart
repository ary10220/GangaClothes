import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/network/api_client.dart';
import 'package:mobile/features/catalog/catalog_models.dart';
import 'package:mobile/features/catalog/catalog_service.dart';

void main() {
  test('builds the exact catalog query and omits empty filters', () {
    expect(
      buildCatalogQuery(
        q: '  camisa  ',
        categoryId: 2,
        seasonId: 3,
        sizeId: 4,
        colorId: 5,
        branchId: 6,
      ),
      {
        'q': 'camisa',
        'categoria_id': 2,
        'temporada_id': 3,
        'talla_id': 4,
        'color_id': 5,
        'sucursal_id': 6,
      },
    );
    expect(buildCatalogQuery(q: ' ', branchId: null), isEmpty);
  });

  test(
    'parses products, variants, availability, options, and inactive branches',
    () async {
      final api = _FakeApi({
        '/catalogo': [
          {
            'id': 10,
            'nombre': 'Camisa Oxford',
            'descripcion': null,
            'marca': 'Ganga',
            'precio_venta': 1234.5,
            'imagen_url': null,
            'categoria_id': 2,
            'coleccion_id': 3,
            'disponible_total': 4,
            'variantes': [
              {
                'id': 11,
                'sku': 'P10-T1-C2',
                'talla_id': 1,
                'talla': 'M',
                'color_id': 2,
                'color': 'Azul',
                'color_hex': '#112233',
                'imagen_url': null,
                'disponible_total': 4,
                'disponibilidad': [
                  {'sucursal_id': 8, 'sucursal': 'Centro', 'disponible': 4},
                ],
              },
            ],
          },
        ],
        '/admin/temporadas': [
          {'id': 1, 'nombre': 'Invierno', 'activo': false},
        ],
        '/admin/categorias': [
          {'id': 2, 'nombre': 'Camisas', 'activo': true},
        ],
        '/admin/tallas': [
          {'id': 1, 'nombre': 'M', 'orden': 2},
        ],
        '/admin/colores': [
          {'id': 2, 'nombre': 'Azul', 'codigo_hex': '#112233', 'activo': false},
        ],
        '/admin/sucursales': [
          {'id': 8, 'nombre': 'Centro', 'activo': true},
          {'id': 9, 'nombre': 'Norte', 'activo': false},
        ],
      });
      final service = CatalogService(api);

      final products = await service.fetchCatalog(const CatalogFilters());
      final options = await service.fetchOptions();

      expect(products.single.name, 'Camisa Oxford');
      expect(products.single.salePrice, 1234.5);
      expect(products.single.variants.single.availability.single.available, 4);
      expect(products.single.variants.single.colorHex, '#112233');
      expect(options.seasons.single.active, isFalse);
      expect(options.colors.single.colorHex, '#112233');
      expect(options.branches.last.active, isFalse);
      expect(options.branches.first.displayName, 'Centro');
      expect(formatBolivianos(1234.5), '1.234,50');
      expect(api.queries['/catalogo'], isEmpty);
    },
  );
}

class _FakeApi extends ApiClient {
  _FakeApi(this.responses) : super(dio: Dio());

  final Map<String, Object?> responses;
  final queries = <String, Map<String, dynamic>>{};

  @override
  Future<Response<T>> request<T>(
    String path, {
    String method = 'GET',
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    queries[path] = queryParameters ?? const {};
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: responses[path] as T,
      statusCode: 200,
    );
  }
}
