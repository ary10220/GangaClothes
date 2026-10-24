import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/app/theme.dart';
import 'package:mobile/core/storage/preferences_storage.dart';
import 'package:mobile/features/auth/session_model.dart';
import 'package:mobile/features/catalog/catalog_detail_models.dart';
import 'package:mobile/features/catalog/catalog_detail_service.dart';
import 'package:mobile/features/catalog/catalog_detail_sheet.dart';
import 'package:mobile/features/catalog/catalog_models.dart';
import 'package:mobile/features/catalog/catalog_screen.dart';
import 'package:mobile/features/catalog/catalog_service.dart';
import 'package:mobile/features/virtual_fitting/virtual_fitting_sheet.dart';

void main() {
  testWidgets('renders loading and retryable error states', (tester) async {
    final api = _FakeCatalogApi()..error = true;
    await tester.pumpWidget(
      _host(CatalogScreen(catalogService: api, preferenceStore: _Prefs())),
    );
    await tester.pumpAndSettle();
    expect(find.text('No se pudo cargar el catálogo'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
  });

  testWidgets('renders the explicit loading state', (tester) async {
    final api = _FakeCatalogApi()..pending = true;
    await tester.pumpWidget(
      _host(CatalogScreen(catalogService: api, preferenceStore: _Prefs())),
    );
    await tester.pump();
    expect(find.text('Cargando…'), findsOneWidget);
  });

  testWidgets('renders no published products and result count', (tester) async {
    final api = _FakeCatalogApi();
    await tester.pumpWidget(
      _host(CatalogScreen(catalogService: api, preferenceStore: _Prefs())),
    );
    await tester.pumpAndSettle();
    expect(find.text('Todavía no hay prendas publicadas.'), findsOneWidget);

    final productsApi = _FakeCatalogApi(products: [_product(available: 2)]);
    await tester.pumpWidget(
      _host(
        CatalogScreen(
          key: const ValueKey('products'),
          catalogService: productsApi,
          preferenceStore: _Prefs(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('1 prenda'), findsOneWidget);
    expect(find.text('Bs 1.234,50'), findsOneWidget);
    expect(find.text('M · L'), findsOneWidget);
    expect(find.text('Ver detalle'), findsOneWidget);
  });

  testWidgets('renders backend promotion values in card and detail', (
    tester,
  ) async {
    final product = _product(
      available: 2,
      salePrice: 1000,
      promotion: const CatalogPromotion(
        id: 4,
        name: 'Oferta de temporada',
        discountType: 'porcentaje',
        value: 15,
        label: '-15%',
        endDate: '2030-12-31',
      ),
      finalPrice: 850,
      discount: 150,
    );
    await tester.pumpWidget(
      _host(
        CatalogScreen(
          catalogService: _FakeCatalogApi(products: [product]),
          detailService: _FakeDetailApi(),
          preferenceStore: _Prefs(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('-15%'), findsOneWidget);
    expect(find.text('Bs 850,00'), findsOneWidget);
    expect(find.text('Bs 1.000,00'), findsOneWidget);
    expect(find.text('M · L'), findsOneWidget);

    await tester.drag(find.byType(ListView), const Offset(0, -420));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ver detalle'));
    await tester.pumpAndSettle();

    expect(find.text('Oferta de temporada'), findsOneWidget);
    expect(find.text('Ahorro: Bs 150,00'), findsOneWidget);
    expect(find.text('Bs 850,00'), findsNWidgets(2));
    expect(find.text('Bs 1.000,00'), findsNWidgets(2));
  });

  testWidgets(
    'keeps the no-promotion card appearance and backend final price',
    (tester) async {
      await tester.pumpWidget(
        _host(
          SizedBox(
            width: 320,
            height: 420,
            child: CatalogProductCard(
              product: _product(
                available: 2,
                salePrice: 500,
                finalPrice: 321,
                discount: 13,
              ),
            ),
          ),
        ),
      );

      expect(find.text('Bs 321,00'), findsOneWidget);
      expect(find.text('Bs 500,00'), findsNothing);
      expect(find.text('Oferta'), findsNothing);
      expect(find.textContaining('Ahorro:'), findsNothing);
    },
  );

  testWidgets('renders zero discount and missing promotion fields safely', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        Scaffold(
          body: CatalogDetailSheet(
            product: _product(
              available: 2,
              salePrice: 900,
              finalPrice: 875.25,
              discount: 0,
              promotion: const CatalogPromotion(id: 8),
            ),
            branches: const [],
            actionService: _FakeDetailApi(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Oferta'), findsOneWidget);
    expect(find.text('Bs 875,25'), findsOneWidget);
    expect(find.text('Bs 900,00'), findsOneWidget);
    expect(find.text('Ahorro: Bs 0,00'), findsOneWidget);
  });

  testWidgets(
    'renders no-stock branch state and guest/authenticated app bars',
    (tester) async {
      final api = _FakeCatalogApi(
        branches: const [
          BranchOption(id: 4, displayName: 'Centro', active: true),
        ],
      );
      final prefs = _Prefs(saved: 4);
      await tester.pumpWidget(
        _host(CatalogScreen(catalogService: api, preferenceStore: prefs)),
      );
      await tester.pumpAndSettle();
      expect(
        find.text('No hay prendas con stock en la sucursal seleccionada.'),
        findsOneWidget,
      );
      expect(find.text('Iniciar sesión'), findsOneWidget);

      await tester.pumpWidget(
        _host(
          CatalogScreen(
            catalogService: _FakeCatalogApi(),
            preferenceStore: _Prefs(),
            session: const Session(
              accessToken: 'token',
              user: User(
                id: 1,
                name: 'Ada',
                email: 'ada@example.com',
                roles: ['cliente'],
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Mis reservas'), findsOneWidget);
      expect(find.text('Carrito'), findsOneWidget);
      expect(find.text('Asistente'), findsNothing);
      expect(find.text('Iniciar sesión'), findsNothing);
    },
  );

  testWidgets('opens the real detail sheet from a catalog card', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        CatalogScreen(
          catalogService: _FakeCatalogApi(products: [_product(available: 2)]),
          detailService: _FakeDetailApi(),
          preferenceStore: _Prefs(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.drag(find.byType(ListView), const Offset(0, -420));
    await tester.pumpAndSettle();
    final detailAction = find.ancestor(
      of: find.text('Ver detalle'),
      matching: find.byType(TextButton),
    );
    await tester.tap(detailAction);
    await tester.pumpAndSettle();

    expect(find.text('DETALLE DE LA PRENDA'), findsOneWidget);
    expect(
      find.text('Para reservar o comprar necesitas una cuenta de cliente.'),
      findsOneWidget,
    );
    expect(find.text('Iniciar sesión'), findsNWidgets(2));
  });

  testWidgets('shows virtual fitting only when a selected image exists', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        Scaffold(
          body: CatalogDetailSheet(
            product: _product(available: 2),
            branches: const [],
            actionService: _FakeDetailApi(),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Vestidor virtual'), findsNothing);

    await tester.pumpWidget(
      _host(
        Scaffold(
          body: CatalogDetailSheet(
            product: _product(
              available: 2,
              productImageUrl: 'https://cdn.example.com/product.jpg',
            ),
            branches: const [],
            actionService: _FakeDetailApi(),
            cameraEnumerator: () async => const [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Vestidor virtual'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('Vestidor virtual'),
      -240,
      scrollable: find.byType(Scrollable),
    );
    await tester.tap(find.text('Vestidor virtual'));
    await tester.pumpAndSettle();
    expect(find.text('VESTIDOR VIRTUAL'), findsOneWidget);
    expect(
      tester
          .widget<VirtualFittingSheet>(find.byType(VirtualFittingSheet))
          .imageUrl,
      'https://cdn.example.com/product.jpg',
    );
  });

  testWidgets('selected variant image takes precedence over product image', (
    tester,
  ) async {
    await tester.pumpWidget(
      _host(
        Scaffold(
          body: CatalogDetailSheet(
            product: _product(
              available: 2,
              productImageUrl: 'https://cdn.example.com/product.jpg',
              variantImageUrl: 'https://cdn.example.com/variant.jpg',
            ),
            branches: const [],
            actionService: _FakeDetailApi(),
            cameraEnumerator: () async => const [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Vestidor virtual'),
      -240,
      scrollable: find.byType(Scrollable),
    );
    await tester.tap(find.text('Vestidor virtual'));
    await tester.pumpAndSettle();

    expect(
      tester
          .widget<VirtualFittingSheet>(find.byType(VirtualFittingSheet))
          .imageUrl,
      'https://cdn.example.com/variant.jpg',
    );
  });

  testWidgets('passes the latest transparent PNG of the variant, resolved '
      'against the product photo', (tester) async {
    await tester.pumpWidget(
      _host(
        Scaffold(
          body: CatalogDetailSheet(
            product: _product(
              available: 2,
              productImageUrl: 'https://cdn.example.com/img/product.jpg',
              arResources: const [
                ArResource(
                  id: 1,
                  type: 'png_overlay',
                  url: 'https://old.example.com/old.png',
                  scale: 1,
                ),
                ArResource(
                  id: 2,
                  type: 'png_overlay',
                  url: '/img/prendas/camisa.png',
                  scale: 1.2,
                ),
                ArResource(id: 3, type: 'modelo_3d', url: '/x.glb', scale: 1),
              ],
            ),
            branches: const [],
            actionService: _FakeDetailApi(),
            cameraEnumerator: () async => const [],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Vestidor virtual'),
      -240,
      scrollable: find.byType(Scrollable),
    );
    await tester.tap(find.text('Vestidor virtual'));
    await tester.pumpAndSettle();

    final sheet = tester.widget<VirtualFittingSheet>(
      find.byType(VirtualFittingSheet),
    );
    expect(sheet.imageUrl, 'https://cdn.example.com/img/product.jpg');
    expect(sheet.overlayUrl, 'https://cdn.example.com/img/prendas/camisa.png');
    expect(sheet.overlayScale, 1.2);
  });

  testWidgets('ellipsizes long branch labels on a narrow detail sheet', (
    tester,
  ) async {
    const longBranchName =
        'Sucursal con un nombre suficientemente largo para desbordar';
    final product = Product(
      id: 1,
      name: 'Camisa Oxford',
      description: null,
      brand: 'Ganga',
      salePrice: 100,
      finalPrice: 100,
      imageUrl: null,
      categoryId: 1,
      collectionId: null,
      availableTotal: 3,
      variants: const [
        Variant(
          id: 1,
          sku: 'SKU-1',
          sizeId: 1,
          sizeName: 'M',
          colorId: 1,
          colorName: 'Azul',
          colorHex: '#112233',
          imageUrl: null,
          availableTotal: 3,
          availability: [
            Availability(branchId: 1, branchName: longBranchName, available: 3),
          ],
        ),
      ],
    );

    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(size: Size(280, 700)),
        child: _host(
          Scaffold(
            body: CatalogDetailSheet(
              product: product,
              branches: const [],
              actionService: _FakeDetailApi(),
              session: const Session(
                accessToken: 'token',
                user: User(
                  id: 1,
                  name: 'Ada',
                  email: 'ada@example.com',
                  roles: ['cliente'],
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(
      find.byWidgetPredicate(
        (widget) =>
            widget is Text &&
            widget.maxLines == 1 &&
            widget.overflow == TextOverflow.ellipsis,
      ),
      findsWidgets,
    );
  });
}

Widget _host(Widget child) => MaterialApp(theme: gangaTheme(), home: child);

class _Prefs implements BranchPreferenceStore {
  _Prefs({this.saved});
  int? saved;

  @override
  Future<int?> readSelectedBranch() async => saved;

  @override
  Future<void> saveSelectedBranch(int? branchId) async => saved = branchId;
}

class _FakeCatalogApi implements CatalogDataSource {
  _FakeCatalogApi({this.branches = const [], this.products = const []});

  final List<BranchOption> branches;
  bool error = false;
  bool pending = false;
  final List<Product> products;

  @override
  Future<List<Product>> fetchCatalog(CatalogFilters filters) async {
    if (error) throw StateError('backend unavailable');
    if (pending) return Completer<List<Product>>().future;
    return products;
  }

  @override
  Future<CatalogOptions> fetchOptions() async {
    if (pending) return Completer<CatalogOptions>().future;
    return CatalogOptions(branches: branches);
  }
}

class _FakeDetailApi implements CatalogActionDataSource {
  @override
  Future<ReservationSummary> createReservation(
    ReservationRequest request,
  ) async => const ReservationSummary(
    id: 1,
    branchId: 1,
    branchName: 'Centro',
    visitAt: null,
  );

  @override
  Future<CartSummary?> fetchCart() async => null;

  @override
  Future<CartSummary> openCart({required int branchId}) async => CartSummary(
    id: 1,
    branchId: branchId,
    branchName: 'Centro',
    units: 0,
    total: 0,
    detail: const [],
  );

  @override
  Future<CartSummary> addCartItem({
    required int variantId,
    required int quantity,
  }) async => const CartSummary(
    id: 1,
    branchId: 1,
    branchName: 'Centro',
    units: 1,
    total: 1,
    detail: [],
  );
}

Product _product({
  required int available,
  double salePrice = 1234.5,
  double finalPrice = 1234.5,
  double? discount,
  CatalogPromotion? promotion,
  String? productImageUrl,
  String? variantImageUrl,
  List<ArResource> arResources = const [],
}) => Product(
  id: 1,
  name: 'Camisa Oxford',
  description: null,
  brand: 'Ganga',
  salePrice: salePrice,
  finalPrice: finalPrice,
  discount: discount,
  promotion: promotion,
  imageUrl: productImageUrl,
  categoryId: 1,
  collectionId: null,
  availableTotal: available,
  variants: [
    Variant(
      id: 1,
      sku: 'SKU-1',
      sizeId: 1,
      sizeName: 'M',
      colorId: 1,
      colorName: 'Azul',
      colorHex: '#112233',
      imageUrl: variantImageUrl,
      availableTotal: 1,
      availability: [],
      hasFittingRoom: arResources.isNotEmpty,
      arResources: arResources,
    ),
    Variant(
      id: 2,
      sku: 'SKU-2',
      sizeId: 2,
      sizeName: 'L',
      colorId: 1,
      colorName: 'Azul',
      colorHex: '#112233',
      imageUrl: null,
      availableTotal: 1,
      availability: [],
    ),
  ],
);
