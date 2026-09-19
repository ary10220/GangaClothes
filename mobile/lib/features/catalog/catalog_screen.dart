import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../core/network/api_client.dart';
import '../../core/storage/preferences_storage.dart';
import '../../features/auth/session_model.dart';
import '../../shared/widgets/gc_app_bar.dart';
import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_chip.dart';
import '../../shared/widgets/gc_feedback.dart';
import '../../shared/widgets/gc_loading_empty_error.dart';
import 'catalog_controller.dart';
import 'catalog_detail_service.dart';
import 'catalog_detail_sheet.dart';
import 'catalog_models.dart';
import 'catalog_service.dart';

class CatalogScreen extends StatefulWidget {
  const CatalogScreen({
    this.apiClient,
    this.preferencesStorage,
    this.catalogService,
    this.detailService,
    this.preferenceStore,
    this.session,
    this.onLogout,
    super.key,
  });

  final ApiClient? apiClient;
  final PreferencesStorage? preferencesStorage;
  final CatalogDataSource? catalogService;
  final CatalogActionDataSource? detailService;
  final BranchPreferenceStore? preferenceStore;
  final Session? session;
  final VoidCallback? onLogout;

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  late final CatalogController _controller;
  late final TextEditingController _searchController;

  @override
  void initState() {
    super.initState();
    final source =
        widget.catalogService ??
        CatalogService(
          widget.apiClient ?? (throw StateError('Catalog API is required')),
        );
    final preferences =
        widget.preferenceStore ??
        widget.preferencesStorage ??
        (throw StateError('Catalog preferences are required'));
    _controller = CatalogController(api: source, preferences: preferences);
    _searchController = TextEditingController();
    _controller.addListener(_onControllerChanged);
    _controller.load();
  }

  void _onControllerChanged() {
    if (!mounted) return;
    if (_searchController.text != _controller.filters.search) {
      _searchController.value = _searchController.value.copyWith(
        text: _controller.filters.search,
        selection: TextSelection.collapsed(
          offset: _controller.filters.search.length,
        ),
      );
    }
    setState(() {});
  }

  @override
  void dispose() {
    _controller
      ..removeListener(_onControllerChanged)
      ..dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildAppBar(context),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(14, 16, 14, 36),
          children: [
            _buildFilters(),
            const SizedBox(height: 18),
            _buildResults(),
          ],
        ),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(BuildContext context) {
    final isCustomer = widget.session?.user.roles.contains('cliente') ?? false;
    final destinations = <GcAppBarDestination>[
      GcAppBarDestination(label: 'Catálogo', selected: true, onPressed: () {}),
      if (isCustomer)
        GcAppBarDestination(
          label: 'Mis reservas',
          onPressed: () =>
              Navigator.of(context).pushNamed(AppRoutes.reservations),
        ),
      if (isCustomer)
        GcAppBarDestination(
          label: 'Carrito',
          onPressed: () => Navigator.of(context).pushNamed(AppRoutes.cart),
        ),
      if (widget.session == null)
        GcAppBarDestination(
          label: 'Iniciar sesión',
          onPressed: () => Navigator.of(context).pushNamed(
            AppRoutes.login,
            arguments: const AuthRouteArguments(returnTo: AppRoutes.catalog),
          ),
        ),
      if (widget.session == null)
        GcAppBarDestination(
          label: 'Crear cuenta',
          onPressed: () => Navigator.of(context).pushNamed(
            AppRoutes.register,
            arguments: const AuthRouteArguments(returnTo: AppRoutes.catalog),
          ),
        ),
    ];

    return GcAppBar(
      destinations: destinations,
      accountName: widget.session?.user.fullName,
      accountRole: widget.session?.user.roles.firstOrNull,
      onAccountPressed: widget.session == null ? null : () {},
      onLogout: widget.session == null ? null : widget.onLogout,
    );
  }

  Widget _buildFilters() {
    final filters = _controller.filters;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('CATÁLOGO', style: GangaTextStyles.eyebrow),
        const SizedBox(height: 5),
        const Text('Prendas publicadas', style: GangaTextStyles.heading),
        const SizedBox(height: 14),
        if (_controller.branches.isNotEmpty)
          DropdownButtonFormField<int>(
            initialValue: filters.branchId ?? 0,
            decoration: const InputDecoration(
              labelText: 'Sucursal',
              helperText: 'Elige una tienda o mira el stock de todas.',
            ),
            items: [
              const DropdownMenuItem(
                value: 0,
                child: Text('Todas las sucursales'),
              ),
              ..._controller.branches.map(
                (branch) => DropdownMenuItem(
                  value: branch.id,
                  child: Text(branch.displayName),
                ),
              ),
            ],
            onChanged: (value) =>
                _controller.selectBranch(value == 0 ? null : value),
          ),
        const SizedBox(height: 12),
        TextField(
          controller: _searchController,
          onChanged: _controller.setSearch,
          textInputAction: TextInputAction.search,
          decoration: const InputDecoration(
            hintText: '⌕ Buscar prenda…',
            prefixIcon: Icon(Icons.search),
          ),
        ),
        _buildFilterGroup(
          'Temporada',
          _controller.seasons,
          (id) => _controller.toggleSeason(id),
        ),
        _buildFilterGroup(
          'Categoría',
          _controller.categories,
          (id) => _controller.toggleCategory(id),
        ),
        _buildFilterGroup(
          'Talla',
          _controller.sizes,
          (id) => _controller.toggleSize(id),
        ),
        if (_controller.colors.isNotEmpty) ...[
          const SizedBox(height: 13),
          const Text('COLOR', style: GangaTextStyles.eyebrow),
          const SizedBox(height: 7),
          Wrap(
            spacing: 11,
            runSpacing: 10,
            children: _controller.colors
                .map(
                  (color) => _ColorFilter(
                    option: color,
                    selected: filters.colorId == color.id,
                    onTap: () => _controller.toggleColor(color.id),
                  ),
                )
                .toList(),
          ),
        ],
        if (_controller.hasFilters) ...[
          const SizedBox(height: 14),
          GcButton(
            label: 'Limpiar filtros',
            variant: GcButtonVariant.outlined,
            onPressed: _controller.clearFilters,
          ),
        ],
      ],
    );
  }

  Widget _buildFilterGroup(
    String label,
    List<CatalogOption> options,
    ValueChanged<int> onTap,
  ) {
    if (options.isEmpty) return const SizedBox.shrink();
    final filters = _controller.filters;
    final selected = switch (label) {
      'Temporada' => filters.seasonId,
      'Categoría' => filters.categoryId,
      _ => filters.sizeId,
    };
    return Padding(
      padding: const EdgeInsets.only(top: 13),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(), style: GangaTextStyles.eyebrow),
          const SizedBox(height: 7),
          Wrap(
            spacing: 7,
            runSpacing: 7,
            children: options
                .map(
                  (option) => GcChip(
                    label: option.displayName,
                    selected: option.id == selected,
                    onTap: () => onTap(option.id),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildResults() {
    if (_controller.loading && _controller.products.isEmpty) {
      return const GcLoadingEmptyError(state: GcPanelState.loading);
    }
    if (_controller.error != null) {
      return GcLoadingEmptyError(
        state: GcPanelState.error,
        errorTitle: 'No se pudo cargar el catálogo',
        errorMessage: _controller.error!.message,
        retryLabel: 'Reintentar',
        onRetry: _controller.retry,
      );
    }
    if (_controller.products.isEmpty) {
      if (_controller.filters.branchId != null) {
        return Column(
          children: [
            const GcFeedback(
              message: 'No hay prendas con stock en la sucursal seleccionada.',
            ),
            const SizedBox(height: 10),
            GcButton(
              label: 'Ver todas las sucursales',
              variant: GcButtonVariant.primary,
              onPressed: () => _controller.selectBranch(null),
            ),
            if (_controller.hasFilters) ...[
              const SizedBox(height: 8),
              GcButton(
                label: 'Limpiar filtros',
                variant: GcButtonVariant.outlined,
                onPressed: _controller.clearFilters,
              ),
            ],
          ],
        );
      }
      return GcLoadingEmptyError(
        state: GcPanelState.empty,
        emptyTitle: _controller.hasFilters
            ? 'Ninguna prenda coincide con los filtros elegidos.'
            : 'Todavía no hay prendas publicadas.',
        emptyMessage: _controller.hasFilters
            ? 'Prueba quitando algún filtro.'
            : 'Vuelve a consultar más tarde.',
      );
    }

    final branchName = _selectedBranchName;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '${_controller.products.length} ${_controller.products.length == 1 ? 'prenda' : 'prendas'}'
          '${branchName == null ? ' · en todas las sucursales' : ' · con stock en $branchName'}',
          style: GangaTextStyles.eyebrow,
        ),
        const SizedBox(height: 11),
        LayoutBuilder(
          builder: (context, constraints) {
            final columns = constraints.maxWidth >= 360 ? 2 : 1;
            return GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _controller.products.length,
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: columns,
                crossAxisSpacing: 11,
                mainAxisSpacing: 11,
                childAspectRatio: columns == 2 ? 0.67 : 0.9,
              ),
              itemBuilder: (context, index) => CatalogProductCard(
                product: _controller.products[index],
                branchName: branchName,
                onDetails: () =>
                    _showDetail(context, _controller.products[index]),
              ),
            );
          },
        ),
      ],
    );
  }

  String? get _selectedBranchName {
    final id = _controller.filters.branchId;
    if (id == null) return null;
    return _controller.branches
        .where((branch) => branch.id == id)
        .map((branch) => branch.displayName)
        .firstOrNull;
  }

  void _showDetail(BuildContext context, Product product) {
    final actionService =
        widget.detailService ??
        (widget.apiClient == null
            ? null
            : CatalogActionService(widget.apiClient!));
    if (actionService == null) return;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GangaColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => CatalogDetailSheet(
        product: product,
        branches: _controller.branches,
        actionService: actionService,
        preferredBranchId: _controller.filters.branchId,
        session: widget.session,
        onAvailabilityChanged: _controller.retry,
      ),
    );
  }
}

class CatalogProductCard extends StatelessWidget {
  const CatalogProductCard({
    required this.product,
    this.branchName,
    this.onDetails,
    super.key,
  });

  final Product product;
  final String? branchName;
  final VoidCallback? onDetails;

  @override
  Widget build(BuildContext context) {
    final available = product.availableTotal > 0;
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onDetails,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _ProductImage(product)),
            Padding(
              padding: const EdgeInsets.fromLTRB(11, 9, 11, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.name,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 12.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (product.brand != null)
                    Text(
                      product.brand!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 11,
                        color: GangaColors.gray,
                      ),
                    ),
                  const SizedBox(height: 3),
                  Text(
                    'Bs ${formatBolivianos(product.salePrice)}',
                    style: GangaTextStyles.money,
                  ),
                  const SizedBox(height: 2),
                  Text(
                    availabilityText(product, branchName: branchName),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 10.5,
                      color: available
                          ? GangaColors.success
                          : GangaColors.alert,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    distinctProductSizes(product).join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GangaTextStyles.metadata,
                  ),
                  if (onDetails != null)
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: onDetails,
                        style: TextButton.styleFrom(
                          minimumSize: const Size(0, 36),
                          padding: EdgeInsets.zero,
                        ),
                        child: const Text('Ver detalle'),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProductImage extends StatelessWidget {
  const _ProductImage(this.product);

  final Product product;

  @override
  Widget build(BuildContext context) {
    final image = product.imageUrl?.trim();
    return Container(
      width: double.infinity,
      color: const Color(0xFFECECE5),
      child: image == null || image.isEmpty
          ? const Center(
              child: Icon(
                Icons.image_not_supported_outlined,
                size: 52,
                color: GangaColors.missingImage,
              ),
            )
          : Image.network(
              image,
              fit: BoxFit.cover,
              errorBuilder: (_, _, _) => const Center(
                child: Icon(
                  Icons.image_not_supported_outlined,
                  size: 52,
                  color: GangaColors.missingImage,
                ),
              ),
            ),
    );
  }
}

class _ColorFilter extends StatelessWidget {
  const _ColorFilter({
    required this.option,
    required this.selected,
    required this.onTap,
  });

  final CatalogOption option;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final validHex = isValidColorHex(option.colorHex);
    return Semantics(
      button: true,
      toggled: selected,
      label: option.displayName,
      child: InkWell(
        onTap: onTap,
        customBorder: const CircleBorder(),
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: validHex ? colorFromHex(option.colorHex!) : GangaColors.soft,
            border: Border.all(color: GangaColors.line, width: 1.5),
            boxShadow: selected
                ? [const BoxShadow(color: GangaColors.ink, spreadRadius: 2)]
                : null,
          ),
          child: validHex
              ? null
              : const Icon(
                  Icons.help_outline,
                  size: 16,
                  color: GangaColors.gray,
                ),
        ),
      ),
    );
  }
}

bool isValidColorHex(String? value) =>
    RegExp(r'^#[0-9a-f]{6}$', caseSensitive: false).hasMatch(value ?? '');

Color colorFromHex(String value) =>
    Color(int.parse(value.substring(1), radix: 16) | 0xFF000000);

List<String> distinctProductSizes(Product product) => product.variants
    .map((variant) => variant.sizeName)
    .where((size) => size.isNotEmpty)
    .toSet()
    .toList(growable: false);

String availabilityText(Product product, {String? branchName}) {
  if (branchName != null) {
    return product.availableTotal > 0
        ? '${product.availableTotal} disponibles en $branchName'
        : 'Agotado por ahora';
  }
  if (product.availableTotal <= 0) return 'Agotado por ahora';
  final branches = product.variants
      .expand((variant) => variant.availability)
      .where((row) => row.available > 0)
      .map((row) => row.branchId)
      .toSet()
      .length;
  return '${product.availableTotal} disponibles en $branches ${branches == 1 ? 'sucursal' : 'sucursales'}';
}
