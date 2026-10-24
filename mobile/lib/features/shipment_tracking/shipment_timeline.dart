import 'package:flutter/material.dart';

import '../../app/theme.dart';
import 'shipment_models.dart';

class ShipmentTimeline extends StatelessWidget {
  const ShipmentTimeline({required this.shipment, super.key});

  final Shipment shipment;

  @override
  Widget build(BuildContext context) {
    final entries = <({String label, DateTime? date})>[
      (label: 'Creación', date: shipment.createdAt),
      (label: 'Asignación', date: shipment.assignedAt),
      (label: 'Salida', date: shipment.departedAt),
      (label: 'Entrega estimada', date: shipment.estimatedAt),
      (label: 'Entrega', date: shipment.deliveredAt),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('LÍNEA DE TIEMPO', style: GangaTextStyles.eyebrow),
        const SizedBox(height: 8),
        for (var index = 0; index < entries.length; index++)
          _TimelineRow(
            label: entries[index].label,
            date: entries[index].date,
            isLast: index == entries.length - 1,
          ),
      ],
    );
  }
}

class _TimelineRow extends StatelessWidget {
  const _TimelineRow({
    required this.label,
    required this.date,
    required this.isLast,
  });

  final String label;
  final DateTime? date;
  final bool isLast;

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 42,
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 22,
          child: Column(
            children: [
              Icon(
                date == null
                    ? Icons.radio_button_unchecked
                    : Icons.check_circle,
                size: 16,
                color: date == null ? GangaColors.gray : GangaColors.success,
              ),
              if (!isLast)
                Expanded(child: Container(width: 1, color: GangaColors.line)),
            ],
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            '$label: ${date == null ? 'Sin fecha suministrada' : formatShipmentDate(date)}',
            style: const TextStyle(fontSize: 12, color: GangaColors.gray),
          ),
        ),
      ],
    ),
  );
}
