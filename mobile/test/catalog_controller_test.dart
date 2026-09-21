import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/storage/preferences_storage.dart';
import 'package:mobile/features/catalog/catalog_controller.dart';
import 'package:mobile/features/catalog/catalog_models.dart';
import 'package:mobile/features/catalog/catalog_service.dart';

void main() {
  test(
    'debounces search, toggles chips, and clears filters without a network client',
    () async {
      final api = _FakeCatalogApi();
      final controller = CatalogController(
        api: api,
        preferences: _FakePreferences(),
      );

      await controller.load();
      expect(api.filters.length, 1);
      controller.setSearch('camisa');
      expect(api.filters.length, 1);
      await Future<void>.delayed(const Duration(milliseconds: 360));
      expect(api.filters.last.search, 'camisa');

      controller.toggleCategory(2);
      await Future<void>.delayed(Duration.zero);
      expect(api.filters.last.categoryId, 2);
      controller.toggleCategory(2);
      await Future<void>.delayed(Duration.zero);
      expect(api.filters.last.categoryId, isNull);

      controller.clearFilters();
      await Future<void>.delayed(Duration.zero);
      expect(controller.hasFilters, isFalse);
      expect(api.filters.last.toQuery(), isEmpty);
      controller.dispose();
    },
  );

  test(
    'retains an active saved branch and clears an inactive or missing branch',
    () async {
      final activePreferences = _FakePreferences(saved: 7);
      final activeController = CatalogController(
        api: _FakeCatalogApi(
          branches: const [
            BranchOption(id: 7, displayName: 'Centro', active: true),
          ],
        ),
        preferences: activePreferences,
      );
      await activeController.load();
      expect(activeController.filters.branchId, 7);
      expect(activePreferences.saved, 7);
      activeController.dispose();

      final inactivePreferences = _FakePreferences(saved: 8);
      final inactiveController = CatalogController(
        api: _FakeCatalogApi(
          branches: const [
            BranchOption(id: 8, displayName: 'Norte', active: false),
          ],
        ),
        preferences: inactivePreferences,
      );
      await inactiveController.load();
      expect(inactiveController.filters.branchId, isNull);
      expect(inactivePreferences.saved, isNull);
      inactiveController.dispose();
    },
  );

  test('discards a stale response after filters change', () async {
    final api = _QueuedCatalogApi();
    final controller = CatalogController(
      api: api,
      preferences: _FakePreferences(),
    );
    final loading = controller.load();
    await Future<void>.delayed(Duration.zero);
    controller.toggleCategory(2);
    api.responses[0].complete([_product('old')]);
    api.responses[1].complete([_product('new')]);
    await loading;
    await Future<void>.delayed(Duration.zero);
    expect(controller.products.single.name, 'new');
    controller.dispose();
  });
}

class _FakePreferences implements BranchPreferenceStore {
  _FakePreferences({this.saved});

  int? saved;

  @override
  Future<int?> readSelectedBranch() async => saved;

  @override
  Future<void> saveSelectedBranch(int? branchId) async => saved = branchId;
}

class _FakeCatalogApi implements CatalogDataSource {
  _FakeCatalogApi({this.branches = const []});

  final List<BranchOption> branches;
  final filters = <CatalogFilters>[];

  @override
  Future<List<Product>> fetchCatalog(CatalogFilters filters) async {
    this.filters.add(filters);
    return const [];
  }

  @override
  Future<CatalogOptions> fetchOptions() async =>
      CatalogOptions(branches: branches);
}

class _QueuedCatalogApi implements CatalogDataSource {
  final responses = <Completer<List<Product>>>[];

  @override
  Future<List<Product>> fetchCatalog(CatalogFilters filters) {
    final completer = Completer<List<Product>>();
    responses.add(completer);
    return completer.future;
  }

  @override
  Future<CatalogOptions> fetchOptions() async => const CatalogOptions();
}

Product _product(String name) => Product(
  id: 1,
  name: name,
  description: null,
  brand: null,
  salePrice: 10,
  finalPrice: 10,
  imageUrl: null,
  categoryId: 2,
  collectionId: null,
  availableTotal: 0,
  variants: const [],
);
