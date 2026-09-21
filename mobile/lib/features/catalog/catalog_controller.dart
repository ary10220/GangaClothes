import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../core/network/api_error.dart';
import '../../core/storage/preferences_storage.dart';
import 'catalog_models.dart';
import 'catalog_service.dart';
import '../ai/ai_service.dart';

class CatalogFilterState {
  const CatalogFilterState({
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

  CatalogFilters toFilters() => CatalogFilters(
    search: search,
    categoryId: categoryId,
    seasonId: seasonId,
    sizeId: sizeId,
    colorId: colorId,
    branchId: branchId,
  );

  bool get hasFilters =>
      search.trim().isNotEmpty ||
      categoryId != null ||
      seasonId != null ||
      sizeId != null ||
      colorId != null;

  CatalogFilterState copyWith({
    String? search,
    Object? categoryId = _keep,
    Object? seasonId = _keep,
    Object? sizeId = _keep,
    Object? colorId = _keep,
    Object? branchId = _keep,
  }) => CatalogFilterState(
    search: search ?? this.search,
    categoryId: identical(categoryId, _keep)
        ? this.categoryId
        : categoryId as int?,
    seasonId: identical(seasonId, _keep) ? this.seasonId : seasonId as int?,
    sizeId: identical(sizeId, _keep) ? this.sizeId : sizeId as int?,
    colorId: identical(colorId, _keep) ? this.colorId : colorId as int?,
    branchId: identical(branchId, _keep) ? this.branchId : branchId as int?,
  );
}

const _keep = Object();

class CatalogController extends ChangeNotifier {
  CatalogController({
    required this.api,
    required this.preferences,
    this.aiEventSink,
  });

  final CatalogDataSource api;
  final BranchPreferenceStore preferences;
  final AiEventSink? aiEventSink;

  CatalogFilterState _filters = const CatalogFilterState();
  CatalogFilterState get filters => _filters;

  List<Product> products = const [];
  List<CatalogOption> seasons = const [];
  List<CatalogOption> categories = const [];
  List<CatalogOption> sizes = const [];
  List<CatalogOption> colors = const [];
  List<BranchOption> branches = const [];
  ApiError? error;
  bool loading = true;
  bool loaded = false;

  Timer? _searchTimer;
  int _requestVersion = 0;
  int _loadVersion = 0;
  bool _disposed = false;
  final Set<String> _reportedSearchEvents = <String>{};

  bool get hasFilters => _filters.hasFilters;

  Future<void> load() async {
    final loadVersion = ++_loadVersion;
    loading = true;
    error = null;
    _notify();

    final savedBranch = await preferences.readSelectedBranch();
    CatalogOptions options;
    try {
      options = await api.fetchOptions();
    } catch (_) {
      // The catalog remains browseable when filter resources are unavailable.
      options = const CatalogOptions();
    }
    if (_disposed || loadVersion != _loadVersion) return;

    seasons = options.seasons
        .where((option) => option.active)
        .toList(growable: false);
    categories = options.categories
        .where((option) => option.active)
        .toList(growable: false);
    sizes = options.sizes;
    colors = options.colors;
    branches = options.branches
        .where((branch) => branch.active)
        .toList(growable: false);

    final activeBranch =
        savedBranch != null &&
            branches.any((branch) => branch.id == savedBranch)
        ? savedBranch
        : null;
    if (activeBranch != savedBranch) await preferences.saveSelectedBranch(null);
    _filters = _filters.copyWith(branchId: activeBranch);
    _notify();
    await _fetch(++_requestVersion);
  }

  void setSearch(String value) {
    _filters = _filters.copyWith(search: value);
    final version = ++_requestVersion;
    _searchTimer?.cancel();
    _notify();
    _searchTimer = Timer(
      const Duration(milliseconds: 350),
      () => _fetch(version),
    );
  }

  void toggleCategory(int id) => _toggle('category', id);

  void toggleSeason(int id) => _toggle('season', id);

  void toggleSize(int id) => _toggle('size', id);

  void toggleColor(int id) => _toggle('color', id);

  void _toggle(String filter, int id) {
    _searchTimer?.cancel();
    final current = switch (filter) {
      'category' => _filters.categoryId,
      'season' => _filters.seasonId,
      'size' => _filters.sizeId,
      _ => _filters.colorId,
    };
    final value = current == id ? null : id;
    _filters = switch (filter) {
      'category' => _filters.copyWith(categoryId: value),
      'season' => _filters.copyWith(seasonId: value),
      'size' => _filters.copyWith(sizeId: value),
      _ => _filters.copyWith(colorId: value),
    };
    _notify();
    _fetch(++_requestVersion);
  }

  Future<void> selectBranch(int? id) async {
    if (id != null && !branches.any((branch) => branch.id == id)) return;
    _searchTimer?.cancel();
    _filters = _filters.copyWith(branchId: id);
    await preferences.saveSelectedBranch(id);
    _notify();
    await _fetch(++_requestVersion);
  }

  void clearFilters() {
    _searchTimer?.cancel();
    _filters = _filters.copyWith(
      search: '',
      categoryId: null,
      seasonId: null,
      sizeId: null,
      colorId: null,
    );
    _notify();
    _fetch(++_requestVersion);
  }

  Future<void> retry() => load();

  Future<void> _fetch(int version) async {
    loading = true;
    error = null;
    _notify();
    try {
      final result = await api.fetchCatalog(_filters.toFilters());
      if (_disposed || version != _requestVersion) return;
      products = result;
      _reportSearchEvents(result);
      loaded = true;
      loading = false;
      _notify();
    } on ApiError catch (caught) {
      if (_disposed || version != _requestVersion) return;
      products = const [];
      loaded = true;
      loading = false;
      error = caught;
      _notify();
    } catch (caught) {
      if (_disposed || version != _requestVersion) return;
      products = const [];
      loaded = true;
      loading = false;
      error = ApiError(statusCode: 0, message: '$caught', cause: caught);
      _notify();
    }
  }

  void _reportSearchEvents(List<Product> result) {
    final sink = aiEventSink;
    final search = _filters.search.trim();
    if (sink == null || search.isEmpty) return;
    for (final product in result) {
      final key = '$search:${product.id}';
      if (_reportedSearchEvents.add(key)) {
        unawaited(
          _bestEffortEvent(sink, productId: product.id, eventType: 'busqueda'),
        );
      }
    }
  }

  Future<void> _bestEffortEvent(
    AiEventSink sink, {
    required int productId,
    required String eventType,
  }) async {
    try {
      await sink.reportProductEvent(productId: productId, eventType: eventType);
    } catch (_) {
      // Analytics failures must not affect catalog loading.
    }
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _searchTimer?.cancel();
    super.dispose();
  }
}
