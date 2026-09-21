import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/cart/cart_models.dart';
import 'package:mobile/features/delivery/delivery_models.dart';

void main() {
  test('parses tariff, complete quote, origin, destination, and totals', () {
    final tariff = DeliveryTariff.fromJson({
      'costo_base': 12,
      'costo_por_km': 3.5,
      'recargo_express_porcentaje': 45,
      'envio_gratis_desde': 500,
      'cobertura_km': 25,
      'minutos_preparacion': 45,
      'minutos_preparacion_express': 15,
      'velocidad_kmh': 18,
    });
    final quote = DeliveryQuote.fromJson({
      'dentro_de_cobertura': true,
      'mensaje_cobertura': null,
      'desglose': [
        {'concepto': 'Costo base', 'detalle': 'Tarifa fija', 'importe': 12},
        {'concepto': 'Envío gratis', 'importe': -20.75},
      ],
      'costo_envio': 0,
      'distancia_km': 4.25,
      'minutos_estimados': 59,
      'entrega_estimada': '2026-09-21T10:00:00',
      'express': true,
      'sucursal': {
        'id': 2,
        'nombre': 'Centro',
        'direccion': 'Calle Principal',
        'latitud': -17.78,
        'longitud': -63.18,
      },
      'destino': {'latitud': -17.79, 'longitud': -63.17},
      'total_a_pagar': 500,
    });

    expect(tariff.coverageKilometers, 25);
    expect(quote.isComplete, isTrue);
    expect(quote.origin?.name, 'Centro');
    expect(quote.destination?.latitude, -17.79);
    expect(quote.breakdown.last.amount, -20.75);
    expect(quote.breakdown.last.isCredit, isTrue);
    expect(quote.shippingCost, 0);
    expect(quote.totalToPay, 500);
  });

  test('blocks incomplete and outside-coverage quotes', () {
    final incomplete = DeliveryQuote.fromJson({
      'dentro_de_cobertura': true,
      'costo_envio': 10,
    });
    final outside = DeliveryQuote.fromJson({
      'dentro_de_cobertura': false,
      'mensaje_cobertura': 'Fuera de cobertura',
      'distancia_km': 40,
    });

    expect(incomplete.isComplete, isFalse);
    expect(outside.withinCoverage, isFalse);
    expect(outside.coverageMessage, 'Fuera de cobertura');
  });

  test('serializes quote and delivery inputs without client totals', () {
    const quoteInput = DeliveryQuoteInput(
      branchId: 2,
      latitude: -17.78,
      longitude: -63.18,
      express: true,
    );
    const deliveryInput = DeliveryInput(
      saleId: 4,
      address: 'Calle 10 #45',
      reference: '  Portón azul  ',
      contactPhone: '70000000',
      latitude: -17.78,
      longitude: -63.18,
      express: true,
    );

    expect(quoteInput.toJson(), {
      'sucursal_id': 2,
      'latitud': -17.78,
      'longitud': -63.18,
      'express': true,
    });
    expect(deliveryInput.toJson(), {
      'venta_id': 4,
      'direccion': 'Calle 10 #45',
      'referencia': 'Portón azul',
      'telefono_contacto': '70000000',
      'latitud': -17.78,
      'longitud': -63.18,
      'express': true,
    });
    expect(deliveryInput.toJson().containsKey('monto_compra'), isFalse);
  });

  test('extends cart shipment parsing without changing existing fields', () {
    final shipment = CartShipment.fromJson({
      'id': 9,
      'estado': 'pendiente',
      'direccion': 'Calle 10 #45',
      'referencia': 'Portón azul',
      'telefono_contacto': '70000000',
      'latitud': -17.78,
      'longitud': -63.18,
      'express': true,
      'distancia_km': 4.2,
      'fecha_estimada': '2026-09-21T10:00:00',
    });

    expect(shipment.id, 9);
    expect(shipment.address, 'Calle 10 #45');
    expect(shipment.contactPhone, '70000000');
    expect(shipment.express, isTrue);
    expect(shipment.distanceKm, 4.2);
  });
}
