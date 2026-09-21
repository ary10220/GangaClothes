import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/catalog/catalog_detail_controller.dart';
import 'package:mobile/features/catalog/catalog_detail_models.dart';
import 'package:mobile/features/catalog/catalog_detail_service.dart';
import 'package:mobile/features/catalog/catalog_models.dart';

void main() {
  test('starts at an available variant and marks unavailable sizes', () {
    final controller = CatalogDetailController(
      product: _product(),
      branches: const [
        BranchOption(id: 1, displayName: 'Centro', active: true),
        BranchOption(id: 2, displayName: 'Norte', active: true),
      ],
      api: _FakeActions(),
      preferredBranchId: 2,
    );

    expect(controller.selectedVariant?.id, 11);
    expect(controller.sizeUnavailable(1), isFalse);
    expect(controller.sizeUnavailable(2), isTrue);
    expect(controller.branchId, 2);
    expect(controller.selectedBranchAvailability, 1);
  });

  test('changing color resolves a valid size combination and branch', () {
    final controller = CatalogDetailController(
      product: _product(),
      branches: const [],
      api: _FakeActions(),
    );

    controller.selectColor(20);

    expect(controller.selectedVariant?.id, 12);
    expect(controller.sizeId, 2);
    expect(controller.branchId, 1);
    expect(controller.actionBlockReason, isNull);
  });

  test('blocks quantities above the selected branch stock', () {
    final controller = CatalogDetailController(
      product: _product(),
      branches: const [],
      api: _FakeActions(),
    );

    controller.setQuantity(3);

    expect(controller.actionBlockReason, contains('Solo hay 2 disponibles'));
  });

  test('reservation uses a local ISO date without timezone', () async {
    final actions = _FakeActions()..reservation = _reservation();
    final controller = CatalogDetailController(
      product: _product(),
      branches: const [],
      api: actions,
    );
    final visit = DateTime.now().add(const Duration(days: 1));
    controller.setVisitAt(DateTime(visit.year, visit.month, visit.day, 11, 30));
    controller.setNotes('  Probador  ');

    controller.enterReservation();
    await controller.createReservation();

    expect(actions.reservationRequest?.branchId, 1);
    expect(actions.reservationRequest?.variantId, 11);
    expect(actions.reservationRequest?.quantity, 1);
    expect(actions.reservationRequest?.notes, 'Probador');
    expect(
      actions.reservationRequest?.toJson()['fecha_hora_prueba'],
      matches(RegExp(r'^\d{4}-\d{2}-\d{2}T11:30:00$')),
    );
    expect(controller.success, contains('Reserva #R-7'));
  });

  test('rejects a reservation date that is not in the future', () async {
    final actions = _FakeActions();
    final controller = CatalogDetailController(
      product: _product(),
      branches: const [],
      api: actions,
    );
    controller.setVisitAt(DateTime.now().subtract(const Duration(minutes: 1)));
    controller.enterReservation();

    await controller.createReservation();

    expect(controller.error, 'Elige una fecha y hora futuras para tu visita.');
    expect(actions.reservationRequest, isNull);
  });

  test('requires confirmation before moving a non-empty cart branch', () async {
    final actions = _FakeActions()
      ..cart = _cart(branchId: 2, branchName: 'Norte', hasItems: true)
      ..addedCart = _cart(branchId: 1, branchName: 'Centro', hasItems: true);
    final controller = CatalogDetailController(
      product: _product(),
      branches: const [],
      api: actions,
    );

    await controller.addToCart();
    expect(controller.cartConflict?.from, 'Norte');
    expect(actions.openedBranches, isEmpty);
    expect(actions.added, isFalse);

    await controller.addToCart(confirmBranchChange: true);
    expect(actions.openedBranches, [1]);
    expect(actions.added, isTrue);
    expect(controller.success, contains('Agregado al carrito'));
  });
}

class _FakeActions implements CatalogActionDataSource {
  ReservationSummary? reservation;
  ReservationRequest? reservationRequest;
  CartSummary? cart;
  CartSummary? addedCart;
  final openedBranches = <int>[];
  bool added = false;

  @override
  Future<ReservationSummary> createReservation(
    ReservationRequest request,
  ) async {
    reservationRequest = request;
    return reservation ?? _reservation();
  }

  @override
  Future<CartSummary?> fetchCart() async => cart;

  @override
  Future<CartSummary> openCart({required int branchId}) async {
    openedBranches.add(branchId);
    return _cart(branchId: branchId, branchName: 'Centro', hasItems: false);
  }

  @override
  Future<CartSummary> addCartItem({
    required int variantId,
    required int quantity,
  }) async {
    added = true;
    return addedCart ??
        _cart(branchId: 1, branchName: 'Centro', hasItems: true);
  }
}

Product _product() => const Product(
  id: 10,
  name: 'Camisa Oxford',
  description: 'Algodón',
  brand: 'Ganga',
  salePrice: 120,
  finalPrice: 120,
  imageUrl: null,
  categoryId: 1,
  collectionId: null,
  availableTotal: 3,
  variants: [
    Variant(
      id: 11,
      sku: 'SKU-11',
      sizeId: 1,
      sizeName: 'M',
      colorId: 10,
      colorName: 'Azul',
      colorHex: '#112233',
      imageUrl: null,
      availableTotal: 3,
      availability: [
        Availability(branchId: 1, branchName: 'Centro', available: 2),
        Availability(branchId: 2, branchName: 'Norte', available: 1),
      ],
    ),
    Variant(
      id: 12,
      sku: 'SKU-12',
      sizeId: 2,
      sizeName: 'L',
      colorId: 20,
      colorName: 'Rojo',
      colorHex: '#FF0000',
      imageUrl: null,
      availableTotal: 1,
      availability: [
        Availability(branchId: 1, branchName: 'Centro', available: 1),
      ],
    ),
    Variant(
      id: 13,
      sku: 'SKU-13',
      sizeId: 2,
      sizeName: 'L',
      colorId: 10,
      colorName: 'Azul',
      colorHex: '#112233',
      imageUrl: null,
      availableTotal: 0,
      availability: [
        Availability(branchId: 1, branchName: 'Centro', available: 0),
      ],
    ),
  ],
);

ReservationSummary _reservation() => const ReservationSummary(
  id: 7,
  branchId: 1,
  branchName: 'Centro',
  visitAt: null,
);

CartSummary _cart({
  required int branchId,
  required String branchName,
  required bool hasItems,
}) => CartSummary(
  id: 1,
  branchId: branchId,
  branchName: branchName,
  units: hasItems ? 1 : 0,
  total: 120,
  detail: hasItems ? const [CartLineSummary(id: 1, variantId: 11)] : const [],
);
