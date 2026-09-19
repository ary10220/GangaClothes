import 'package:flutter/material.dart';

import '../../app/routes.dart';
import '../../app/theme.dart';
import '../../features/auth/session_model.dart';
import '../../shared/widgets/gc_button.dart';
import '../../shared/widgets/gc_chip.dart';
import 'catalog_detail_controller.dart';
import 'catalog_detail_models.dart';
import 'catalog_detail_service.dart';
import 'catalog_models.dart';

class CatalogDetailSheet extends StatefulWidget {
  const CatalogDetailSheet({
    required this.product,
    required this.branches,
    required this.actionService,
    this.preferredBranchId,
    this.session,
    this.onAvailabilityChanged,
    super.key,
  });

  final Product product;
  final List<BranchOption> branches;
  final CatalogActionDataSource actionService;
  final int? preferredBranchId;
  final Session? session;
  final VoidCallback? onAvailabilityChanged;

  @override
  State<CatalogDetailSheet> createState() => _CatalogDetailSheetState();
}

class _CatalogDetailSheetState extends State<CatalogDetailSheet> {
  late final CatalogDetailController _controller;

  @override
  void initState() {
    super.initState();
    _controller = CatalogDetailController(
      product: widget.product,
      branches: widget.branches,
      api: widget.actionService,
      preferredBranchId: widget.preferredBranchId,
    )..addListener(_onChanged);
  }

  void _onChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _controller
      ..removeListener(_onChanged)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.sizeOf(context);
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: media.height * .94),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(18, 10, 18, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 38,
                  height: 4,
                  decoration: BoxDecoration(
                    color: GangaColors.line,
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              _buildHeader(context),
              const SizedBox(height: 16),
              _buildProductInfo(),
              const SizedBox(height: 16),
              _buildSelection(),
              const SizedBox(height: 16),
              _buildActions(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) => Row(
    children: [
      const Expanded(
        child: Text('DETALLE DE LA PRENDA', style: GangaTextStyles.eyebrow),
      ),
      IconButton(
        tooltip: 'Cerrar',
        onPressed: () => Navigator.of(context).pop(),
        icon: const Icon(Icons.close),
      ),
    ],
  );

  Widget _buildProductInfo() {
    final variantImage = _controller.selectedVariant?.imageUrl?.trim();
    final image = variantImage?.isNotEmpty == true
        ? variantImage
        : widget.product.imageUrl?.trim();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _DetailImage(imageUrl: image, name: widget.product.name),
        const SizedBox(height: 14),
        if (widget.product.brand != null)
          Text(widget.product.brand!, style: GangaTextStyles.eyebrow),
        const SizedBox(height: 4),
        Text(widget.product.name, style: GangaTextStyles.subheading),
        const SizedBox(height: 5),
        Text(
          'Bs ${formatBolivianos(widget.product.salePrice)}',
          style: GangaTextStyles.money.copyWith(fontSize: 17),
        ),
        if (widget.product.description?.trim().isNotEmpty == true) ...[
          const SizedBox(height: 8),
          Text(
            widget.product.description!,
            style: const TextStyle(color: GangaColors.gray, height: 1.5),
          ),
        ],
      ],
    );
  }

  Widget _buildSelection() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        'COLOR · ${_controller.selectedVariant?.colorName ?? '—'}',
        style: GangaTextStyles.label,
      ),
      const SizedBox(height: 8),
      Wrap(
        spacing: 12,
        runSpacing: 10,
        children: _controller.colors.map(_colorButton).toList(),
      ),
      const SizedBox(height: 15),
      const Text('TALLA', style: GangaTextStyles.label),
      const SizedBox(height: 8),
      Wrap(
        spacing: 7,
        runSpacing: 7,
        children: _controller.sizes.map(_sizeButton).toList(),
      ),
      const SizedBox(height: 15),
      _buildAvailability(),
      if (_controller.actionBlockReason != null) ...[
        const SizedBox(height: 9),
        Text(
          _controller.actionBlockReason!,
          style: const TextStyle(color: GangaColors.gray, height: 1.4),
        ),
      ],
    ],
  );

  Widget _colorButton(CatalogColorChoice color) {
    final validHex = isValidColorHex(color.hex);
    final selected = color.id == _controller.colorId;
    return Semantics(
      button: true,
      toggled: selected,
      label: color.name,
      child: InkWell(
        onTap: () => _controller.selectColor(color.id),
        customBorder: const CircleBorder(),
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: validHex ? colorFromHex(color.hex!) : GangaColors.soft,
            border: Border.all(color: GangaColors.line, width: 1.5),
            boxShadow: selected
                ? [const BoxShadow(color: GangaColors.ink, spreadRadius: 2)]
                : null,
          ),
          child: validHex
              ? null
              : const Icon(
                  Icons.help_outline,
                  size: 17,
                  color: GangaColors.gray,
                ),
        ),
      ),
    );
  }

  Widget _sizeButton(CatalogSizeChoice size) {
    final unavailable = _controller.sizeUnavailable(size.id);
    final selected = size.id == _controller.sizeId;
    return Semantics(
      button: true,
      enabled: !unavailable,
      toggled: selected,
      label: unavailable ? '${size.name}, agotada en este color' : size.name,
      child: Opacity(
        opacity: unavailable && !selected ? .55 : 1,
        child: GcChip(
          label: size.name,
          selected: selected,
          onTap: unavailable ? null : () => _controller.selectSize(size.id),
          semanticLabel: unavailable ? '${size.name}, agotada' : size.name,
        ),
      ),
    );
  }

  Widget _buildAvailability() {
    final rows = _controller.availability;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _controller.selectedBranchName == null
              ? 'DISPONIBLE POR SUCURSAL'
              : 'DISPONIBLE EN ${_controller.selectedBranchName!.toUpperCase()}',
          style: GangaTextStyles.label,
        ),
        const SizedBox(height: 7),
        Container(
          decoration: BoxDecoration(
            color: GangaColors.white,
            border: Border.all(color: GangaColors.line, width: 1.5),
            borderRadius: BorderRadius.circular(10),
          ),
          child: rows.isEmpty
              ? const Padding(
                  padding: EdgeInsets.all(11),
                  child: Text('Ninguna sucursal · Agotado'),
                )
              : Column(
                  children: [
                    for (var index = 0; index < rows.length; index++) ...[
                      if (index > 0)
                        const Divider(height: 1, color: GangaColors.line),
                      _availabilityRow(rows[index]),
                    ],
                  ],
                ),
        ),
      ],
    );
  }

  Widget _availabilityRow(Availability row) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
    child: Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(child: Text(row.branchName)),
        Text(
          row.available > 0 ? '${row.available} disp.' : 'Agotado',
          style: TextStyle(
            color: row.available > 0 ? GangaColors.success : GangaColors.alert,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    ),
  );

  Widget _buildActions() {
    final isCustomer = widget.session?.user.roles.contains('cliente') ?? false;
    if (widget.session == null) return _buildGuestActions();
    if (!isCustomer) {
      return const Text(
        'Las reservas y compras en línea son para cuentas de cliente. El personal vende desde Caja.',
        style: TextStyle(color: GangaColors.gray, height: 1.5),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (_controller.mode == CatalogDetailMode.reserve)
          _buildReservationForm()
        else ...[
          _buildBranchAndQuantity(),
          if (_controller.cartConflict != null) _buildCartConflict(),
        ],
        if (_controller.error != null) ...[
          const SizedBox(height: 10),
          Text(
            _controller.error!,
            style: const TextStyle(color: GangaColors.alert, height: 1.4),
          ),
        ],
        if (_controller.success != null) _buildSuccess(),
        const SizedBox(height: 12),
        _buildActionButtons(),
      ],
    );
  }

  Widget _buildGuestActions() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const Text(
        'Para reservar o comprar necesitas una cuenta de cliente.',
        style: TextStyle(color: GangaColors.gray, height: 1.5),
      ),
      const SizedBox(height: 12),
      Wrap(
        spacing: 8,
        runSpacing: 8,
        children: [
          GcButton(
            label: 'Iniciar sesión',
            variant: GcButtonVariant.outlined,
            onPressed: () => _openAuth(AppRoutes.login),
          ),
          GcButton(
            label: 'Crear cuenta',
            onPressed: () => _openAuth(AppRoutes.register),
          ),
        ],
      ),
    ],
  );

  Widget _buildBranchAndQuantity() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      if (_controller.branchesWithStock.isNotEmpty)
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: DropdownButtonFormField<int>(
                key: ValueKey(_controller.branchId),
                initialValue: _controller.branchId,
                decoration: const InputDecoration(labelText: 'Sucursal'),
                items: _controller.branchesWithStock
                    .map(
                      (row) => DropdownMenuItem(
                        value: row.branchId,
                        child: Text(
                          '${row.branchName} (${row.available} disp.)',
                        ),
                      ),
                    )
                    .toList(),
                onChanged: (value) {
                  if (value != null) _controller.selectBranch(value);
                },
              ),
            ),
            const SizedBox(width: 10),
            _QuantityControl(
              quantity: _controller.quantity,
              maximum: _controller.selectedBranchAvailability,
              onChanged: _controller.setQuantity,
            ),
          ],
        ),
    ],
  );

  Widget _buildReservationForm() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: GangaColors.soft,
          border: Border.all(color: GangaColors.line, width: 1.5),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'RESERVAR PARA PROBARTE EN ${_controller.selectedBranchName ?? 'TIENDA'}',
              style: GangaTextStyles.eyebrow,
            ),
            const SizedBox(height: 10),
            GcButton(
              expand: true,
              variant: GcButtonVariant.outlined,
              label: _formatVisit(_controller.visitAt),
              icon: const Icon(Icons.event_outlined, size: 17),
              onPressed: _pickVisit,
            ),
            const SizedBox(height: 10),
            TextField(
              maxLength: 200,
              onChanged: _controller.setNotes,
              decoration: const InputDecoration(
                labelText: 'Notas para la tienda',
                hintText: 'Opcional',
                counterText: '',
              ),
            ),
            const SizedBox(height: 7),
            Text(
              'Apartamos ${_controller.quantity} ${_controller.quantity == 1 ? 'unidad' : 'unidades'} hasta tu visita. Puedes cancelar desde «Mis reservas».',
              style: const TextStyle(color: GangaColors.gray, height: 1.4),
            ),
          ],
        ),
      ),
    ],
  );

  Widget _buildCartConflict() {
    final conflict = _controller.cartConflict!;
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: GangaColors.lightError,
        borderRadius: BorderRadius.circular(9),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Tu carrito se despacha desde ${conflict.from}. Si agregas esta prenda desde ${conflict.to}, todo el carrito pasa a despacharse desde ${conflict.to}.',
            style: const TextStyle(color: GangaColors.alert, height: 1.45),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              GcButton(
                label: 'Cancelar',
                variant: GcButtonVariant.outlined,
                onPressed: _clearConflict,
              ),
              GcButton(
                label: 'Cambiar y agregar',
                onPressed: _controller.loading
                    ? null
                    : () => _controller.addToCart(confirmBranchChange: true),
                loading: _controller.loading,
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSuccess() => Container(
    margin: const EdgeInsets.only(top: 10),
    padding: const EdgeInsets.all(11),
    decoration: BoxDecoration(
      color: GangaColors.lightSuccess,
      borderRadius: BorderRadius.circular(9),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(Icons.check_circle_outline, color: GangaColors.success),
        const SizedBox(height: 6),
        Text(
          _controller.success!,
          style: const TextStyle(color: GangaColors.success, height: 1.4),
        ),
        TextButton(
          onPressed: () => _openDestination(
            _controller.successRoute == 'cart'
                ? AppRoutes.cart
                : AppRoutes.reservations,
          ),
          child: Text(
            _controller.successRoute == 'cart'
                ? 'Ir al carrito →'
                : 'Ver mis reservas →',
          ),
        ),
      ],
    ),
  );

  Widget _buildActionButtons() {
    if (_controller.mode == CatalogDetailMode.reserve) {
      return Row(
        children: [
          Expanded(
            child: GcButton(
              label: 'Volver',
              variant: GcButtonVariant.outlined,
              onPressed: _controller.loading
                  ? null
                  : _controller.leaveReservation,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: GcButton(
              label: 'Confirmar reserva',
              loading: _controller.loading,
              onPressed:
                  _controller.loading || _controller.actionBlockReason != null
                  ? null
                  : _controller.createReservation,
            ),
          ),
        ],
      );
    }
    if (_controller.cartConflict != null) return const SizedBox.shrink();
    return Row(
      children: [
        Expanded(
          child: GcButton(
            label: 'Reservar para probar en tienda',
            variant: GcButtonVariant.outlined,
            onPressed:
                _controller.loading || _controller.actionBlockReason != null
                ? null
                : _controller.enterReservation,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: GcButton(
            label: 'Agregar al carrito',
            loading: _controller.loading,
            onPressed:
                _controller.loading || _controller.actionBlockReason != null
                ? null
                : _controller.addToCart,
          ),
        ),
      ],
    );
  }

  Future<void> _pickVisit() async {
    final current =
        _controller.visitAt ?? DateTime.now().add(const Duration(days: 1));
    final today = DateTime.now();
    final date = await showDatePicker(
      context: context,
      initialDate: current.isBefore(today) ? today : current,
      firstDate: today,
      lastDate: DateTime(today.year + 2),
    );
    if (!mounted || date == null) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(current),
    );
    if (!mounted || time == null) return;
    _controller.setVisitAt(
      DateTime(date.year, date.month, date.day, time.hour, time.minute),
    );
  }

  void _openAuth(String route) {
    final navigator = Navigator.of(context);
    navigator.pop();
    navigator.pushNamed(
      route,
      arguments: const AuthRouteArguments(returnTo: AppRoutes.catalog),
    );
  }

  void _openDestination(String route) {
    final navigator = Navigator.of(context);
    navigator.pop();
    widget.onAvailabilityChanged?.call();
    navigator.pushNamed(route);
  }

  void _clearConflict() {
    _controller.cartConflict = null;
    setState(() {});
  }

  String _formatVisit(DateTime? value) {
    if (value == null) return 'Elige día y hora de tu visita';
    final local = value.toLocal();
    return '${local.day.toString().padLeft(2, '0')}/'
        '${local.month.toString().padLeft(2, '0')}/${local.year} · '
        '${local.hour.toString().padLeft(2, '0')}:'
        '${local.minute.toString().padLeft(2, '0')}';
  }
}

class _DetailImage extends StatelessWidget {
  const _DetailImage({required this.imageUrl, required this.name});

  final String? imageUrl;
  final String name;

  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    height: 220,
    decoration: BoxDecoration(
      color: const Color(0xFFECECE5),
      borderRadius: BorderRadius.circular(12),
    ),
    clipBehavior: Clip.antiAlias,
    child: imageUrl == null || imageUrl!.isEmpty
        ? const Center(
            child: Icon(
              Icons.image_not_supported_outlined,
              size: 70,
              color: GangaColors.missingImage,
            ),
          )
        : Image.network(
            imageUrl!,
            fit: BoxFit.cover,
            semanticLabel: name,
            errorBuilder: (_, _, _) => const Center(
              child: Icon(
                Icons.image_not_supported_outlined,
                size: 70,
                color: GangaColors.missingImage,
              ),
            ),
          ),
  );
}

class _QuantityControl extends StatelessWidget {
  const _QuantityControl({
    required this.quantity,
    required this.maximum,
    required this.onChanged,
  });

  final int quantity;
  final int maximum;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const Text('CANTIDAD', style: GangaTextStyles.label),
      const SizedBox(height: 7),
      Container(
        height: 48,
        decoration: BoxDecoration(
          color: GangaColors.white,
          border: Border.all(color: GangaColors.line, width: 1.5),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            IconButton(
              tooltip: 'Reducir cantidad',
              onPressed: quantity > 1 ? () => onChanged(quantity - 1) : null,
              icon: const Icon(Icons.remove, size: 18),
            ),
            Text(
              '$quantity',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            IconButton(
              tooltip: 'Aumentar cantidad',
              onPressed: maximum > 0 && quantity < maximum
                  ? () => onChanged(quantity + 1)
                  : null,
              icon: const Icon(Icons.add, size: 18),
            ),
          ],
        ),
      ),
    ],
  );
}

bool isValidColorHex(String? value) =>
    RegExp(r'^#[0-9a-f]{6}$', caseSensitive: false).hasMatch(value ?? '');

Color colorFromHex(String value) =>
    Color(int.parse(value.substring(1), radix: 16) | 0xFF000000);
