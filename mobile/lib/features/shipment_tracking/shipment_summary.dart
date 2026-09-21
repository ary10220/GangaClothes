import 'package:flutter/material.dart';

import '../../app/theme.dart';
import '../../shared/widgets/gc_status_badge.dart';
import '../purchase_history/purchase_history_models.dart';
import 'shipment_models.dart';
import 'shipment_timeline.dart';

class ShipmentSummaryCard extends StatelessWidget {
  const ShipmentSummaryCard({required this.shipment, super.key});

  final Shipment shipment;

  @override
  Widget build(BuildContext context) {
    final origin = shipment.origin;
    final sale = shipment.sale;
    final payment = shipment.payment;
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 13, 14, 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Envío #${shipment.id}',
                    style: GangaTextStyles.subheading,
                  ),
                ),
                GcStatusBadge(
                  text: shipment.stateLabel,
                  variant: shipment.isTerminal
                      ? GcStatusBadgeVariant.success
                      : GcStatusBadgeVariant.neutral,
                  semanticLabel: 'Estado ${shipment.stateLabel}',
                ),
              ],
            ),
            const SizedBox(height: 8),
            if (shipment.address?.trim().isNotEmpty == true)
              _InfoText(label: 'Destino', value: shipment.address!),
            if (shipment.reference?.trim().isNotEmpty == true)
              _InfoText(label: 'Referencia', value: shipment.reference!),
            if (shipment.contactPhone?.trim().isNotEmpty == true)
              _InfoText(label: 'Teléfono', value: shipment.contactPhone!),
            if (shipment.distanceKm != null)
              _InfoText(
                label: 'Distancia',
                value: '${shipment.distanceKm!.toStringAsFixed(2)} km',
              ),
            if (shipment.shippingCost != null)
              _InfoText(
                label: 'Costo de envío',
                value: 'Bs ${formatPurchaseMoney(shipment.shippingCost)}',
              ),
            _InfoText(
              label: 'Tipo',
              value: shipment.express ? 'Express' : 'Estándar',
            ),
            if (shipment.driver?.trim().isNotEmpty == true)
              _InfoText(label: 'Repartidor', value: shipment.driver!),
            if (shipment.cancellationReason?.trim().isNotEmpty == true)
              _InfoText(
                label: 'Motivo de cancelación',
                value: shipment.cancellationReason!,
              ),
            const SizedBox(height: 10),
            const Text(
              'CONTEXTO DE COORDENADAS',
              style: GangaTextStyles.eyebrow,
            ),
            const SizedBox(height: 5),
            Text(
              _coordinates(shipment, origin),
              style: const TextStyle(color: GangaColors.gray, fontSize: 12),
            ),
            const SizedBox(height: 4),
            const Text(
              'El mapa no está disponible en la aplicación móvil; no se calculan rutas ni geocodificación.',
              style: TextStyle(color: GangaColors.gray, fontSize: 11.5),
            ),
            if (origin != null ||
                shipment.customer != null ||
                sale != null ||
                payment != null) ...[
              const SizedBox(height: 10),
              const Divider(),
              if (origin != null) ...[
                const Text('ORIGEN', style: GangaTextStyles.eyebrow),
                _InfoText(label: 'Sucursal', value: origin.name),
                if (origin.address?.trim().isNotEmpty == true)
                  _InfoText(label: 'Dirección', value: origin.address!),
                if (origin.city?.trim().isNotEmpty == true)
                  _InfoText(label: 'Ciudad', value: origin.city!),
              ],
              if (shipment.customer != null) ...[
                const SizedBox(height: 7),
                const Text('CLIENTE', style: GangaTextStyles.eyebrow),
                if (shipment.customer!.name?.trim().isNotEmpty == true)
                  _InfoText(label: 'Nombre', value: shipment.customer!.name!),
                if (shipment.customer!.email?.trim().isNotEmpty == true)
                  _InfoText(label: 'Email', value: shipment.customer!.email!),
              ],
              if (sale != null) ...[
                const SizedBox(height: 7),
                const Text('COMPRA', style: GangaTextStyles.eyebrow),
                if (sale.receiptNumber?.trim().isNotEmpty == true)
                  _InfoText(label: 'Comprobante', value: sale.receiptNumber!),
                _InfoText(label: 'Estado', value: sale.state),
                if (sale.total != null)
                  _InfoText(
                    label: 'Total',
                    value: 'Bs ${formatPurchaseMoney(sale.total)}',
                  ),
              ],
              if (payment != null) ...[
                const SizedBox(height: 7),
                const Text('PAGO', style: GangaTextStyles.eyebrow),
                _InfoText(
                  label: 'Método',
                  value: payment.label ?? payment.method ?? 'No informado',
                ),
                if (payment.gateway?.trim().isNotEmpty == true)
                  _InfoText(label: 'Pasarela', value: payment.gateway!),
                if (payment.amount != null)
                  _InfoText(
                    label: 'Monto',
                    value: 'Bs ${formatPurchaseMoney(payment.amount)}',
                  ),
                if (payment.externalReference?.trim().isNotEmpty == true)
                  _InfoText(
                    label: 'Referencia externa',
                    value: payment.externalReference!,
                  ),
                if (payment.date != null)
                  _InfoText(
                    label: 'Fecha',
                    value: formatShipmentDate(payment.date),
                  ),
              ],
            ],
            if (shipment.items.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Text('PRENDAS', style: GangaTextStyles.eyebrow),
              for (final item in shipment.items)
                Text(
                  '${item.garment} · ${item.size} · ${item.color} ×${item.quantity}',
                  style: const TextStyle(fontSize: 12, color: GangaColors.gray),
                ),
            ],
            const SizedBox(height: 12),
            const Divider(),
            ShipmentTimeline(shipment: shipment),
          ],
        ),
      ),
    );
  }

  String _coordinates(Shipment shipment, ShipmentBranch? origin) {
    final originCoordinates =
        origin?.latitude == null || origin?.longitude == null
        ? 'no suministradas'
        : '${origin!.latitude}, ${origin.longitude}';
    final destinationCoordinates =
        shipment.latitude == null || shipment.longitude == null
        ? 'no suministradas'
        : '${shipment.latitude}, ${shipment.longitude}';
    return 'Origen (${origin?.name ?? 'sucursal'}): $originCoordinates · '
        'destino: $destinationCoordinates';
  }
}

class _InfoText extends StatelessWidget {
  const _InfoText({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Text.rich(
    TextSpan(
      style: const TextStyle(
        color: GangaColors.gray,
        fontSize: 12,
        height: 1.5,
      ),
      children: [
        TextSpan(
          text: '$label: ',
          style: const TextStyle(
            color: GangaColors.ink,
            fontWeight: FontWeight.w700,
          ),
        ),
        TextSpan(text: value),
      ],
    ),
  );
}
