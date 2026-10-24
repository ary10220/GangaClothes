import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/shipment_tracking/shipment_models.dart';

void main() {
  test(
    'parses the paid shipment contract and converts UTC to device local time',
    () {
      final shipment = Shipment.fromJson(_shipmentJson());

      expect(shipment.id, 30);
      expect(shipment.state, ShipmentState.onTheWay);
      expect(shipment.stateLabel, 'En camino');
      expect(shipment.active, isTrue);
      expect(shipment.origin?.name, 'Centro');
      expect(shipment.customer?.phone, '70000000');
      expect(shipment.sale?.isPaid, isTrue);
      expect(shipment.items.single.garment, 'Camisa');
      expect(shipment.payment?.label, 'Tarjeta (Stripe)');
      expect(
        shipment.createdAt,
        DateTime.parse('2030-04-05T09:07:06Z').toLocal(),
      );
      expect(shipment.createdAt?.isUtc, isFalse);
      expect(shipment.estimatedAt, isNotNull);
      expect(shipment.deliveredAt, isNull);
    },
  );

  test(
    'recognizes every supplied shipment state and only terminal states stop',
    () {
      for (final state in ShipmentState.all) {
        final shipment = Shipment.fromJson({
          'id': 1,
          'estado': state,
          'etiqueta_estado': state,
          'activo': ShipmentState.isTerminal(state) ? false : true,
          'venta': {'id': 1, 'estado': 'pagada', 'canal': 'movil'},
        });
        expect(shipment.isTerminal, ShipmentState.isTerminal(state));
      }
    },
  );
}

Map<String, dynamic> _shipmentJson() => {
  'id': 30,
  'estado': 'en_camino',
  'etiqueta_estado': 'En camino',
  'activo': true,
  'direccion': 'Av. Siempre Viva 123',
  'latitud': -17.78,
  'longitud': -63.18,
  'referencia': 'Portón azul',
  'telefono_contacto': '70000000',
  'distancia_km': 4.2,
  'costo_envio': 12.5,
  'express': true,
  'repartidor': 'Alex',
  'motivo_cancelacion': null,
  'fecha_creacion': '2030-04-05T09:07:06Z',
  'fecha_asignacion': '2030-04-05T09:17:06Z',
  'fecha_salida': '2030-04-05T09:27:06Z',
  'fecha_estimada': '2030-04-05T10:07:06Z',
  'fecha_entrega': null,
  'sucursal': {
    'id': 2,
    'nombre': 'Centro',
    'direccion': 'Calle 1',
    'telefono': '3333333',
    'ciudad': 'Santa Cruz',
    'latitud': -17.79,
    'longitud': -63.18,
  },
  'cliente': {
    'id': 8,
    'nombre': 'Cliente',
    'email': 'c@example.com',
    'telefono': '70000000',
  },
  'venta': {
    'id': 12,
    'estado': 'pagada',
    'canal': 'movil',
    'fecha': '2030-04-05T09:07:06Z',
    'nro_comprobante': 'FAC-12',
    'subtotal': 100,
    'descuento': 0,
    'costo_envio': 12.5,
    'total': 112.5,
  },
  'prendas': [
    {
      'id': 3,
      'sku': 'CAM-04',
      'prenda': 'Camisa',
      'talla': 'M',
      'color': 'Azul',
      'cantidad': 1,
    },
  ],
  'pago': {
    'metodo': 'tarjeta',
    'pasarela': 'stripe',
    'etiqueta': 'Tarjeta (Stripe)',
    'monto': 112.5,
    'referencia_externa': 'pay-12',
    'fecha': '2030-04-05T09:07:06Z',
  },
};
