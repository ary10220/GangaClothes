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
            'precio_final': 987.75,
            'descuento': 246.75,
            'promocion': {
              'id': 7,
              'nombre': 'Liquidación Oxford',
              'tipo_descuento': 'monto',
              'valor': 246.75,
              'etiqueta': '-Bs 246,75',
              'fecha_fin': '2030-12-31',
            },
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
          {
            'id': 11,
            'nombre': 'Polo clásico',
            'precio_venta': 80,
            'imagen_url': null,
            'categoria_id': 2,
            'disponible_total': 0,
            'variantes': [],
          },
          {
            'id': 12,
            'nombre': 'Buzo con descuento cero',
            'precio_venta': 120,
            'precio_final': 120,
            'descuento': 0,
            'promocion': {'id': 8, 'nombre': 'Beneficio informativo'},
            'imagen_url': null,
            'categoria_id': 2,
            'disponible_total': 0,
            'variantes': [],
          },
          {
            'id': 13,
            'nombre': 'Oferta incompleta',
            'precio_venta': 50,
            'precio_final': 45,
            'descuento': 5,
            'promocion': {},
            'imagen_url': null,
            'categoria_id': 2,
            'disponible_total': 0,
            'variantes': [],
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

      expect(products.first.name, 'Camisa Oxford');
      expect(products.first.salePrice, 1234.5);
      expect(products.first.finalPrice, 987.75);
      expect(products.first.discount, 246.75);
      expect(products.first.promotion?.label, '-Bs 246,75');
      expect(products.first.promotion?.discountType, 'monto');
      expect(products.first.promotion?.value, 246.75);
      expect(products.first.promotion?.endDate, '2030-12-31');
      expect(products.first.variants.single.availability.single.available, 4);
      expect(products.first.variants.single.colorHex, '#112233');
      expect(products[1].promotion, isNull);
      expect(products[1].finalPrice, 80);
      expect(products[2].discount, 0);
      expect(products[2].promotion?.name, 'Beneficio informativo');
      expect(products[3].promotion, isNotNull);
      expect(products[3].promotion?.label, isNull);
      expect(products[3].finalPrice, 45);
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
