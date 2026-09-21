import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/purchase_history/purchase_history_models.dart';

void main() {
  test(
    'parses the purchase response shape and selects the successful payment',
    () {
      final purchase = Purchase.fromJson({
        'id': '12',
        'estado': 'pagada',
        'canal': 'web',
        'fecha': '2030-04-05T09:07:06',
        'sucursal_id': '2',
        'sucursal': 'Centro',
        'cliente': {'id': 8, 'nombre': 'Cliente', 'email': 'c@example.com'},
        'cajero': null,
        'reserva_id': null,
        'unidades': '2',
        'subtotal': '180.50',
        'descuento': 10,
        'total': 170.5,
        'nro_comprobante': 'FAC-12',
        'tipo_entrega': 'delivery',
        'costo_envio': '12.50',
        'envio': {
          'id': 30,
          'estado': 'en preparación',
          'direccion': 'Av. Siempre Viva 123',
          'referencia': 'Portón azul',
          'total': 12.5,
          'nro_comprobante': 'ENV-30',
          'detalle': <Object?>[],
          'pagos': <Object?>[],
        },
        'detalle': [
          {
            'id': 3,
            'variante_id': 4,
            'sku': 'CAM-04',
            'prenda': 'Camisa',
            'talla': 'M',
            'color': 'Azul',
            'cantidad': 2,
            'precio_unitario': 90.25,
            'precio_final': 80,
            'descuento': 20.5,
            'promocion': {'id': 5, 'nombre': 'Temporada', 'etiqueta': 'SALE'},
            'subtotal': 180.5,
          },
        ],
        'pagos': [
          {
            'id': 1,
            'metodo': 'pasarela',
            'monto': 170.5,
            'estado': 'fallido',
            'referencia_externa': 'old-ref',
          },
          {
            'id': 2,
            'metodo': 'tarjeta',
            'monto': '170.50',
            'estado': 'exitoso',
            'referencia_externa': 'ref-2',
            'pasarela': 'stripe',
            'etiqueta': 'Tarjeta (Stripe)',
          },
        ],
      });

      expect(purchase.id, 12);
      expect(purchase.customer?.email, 'c@example.com');
      expect(purchase.details.single.garment, 'Camisa');
      expect(purchase.details.single.subtotal, 180.5);
      expect(purchase.details.single.finalPrice, 80);
      expect(purchase.details.single.discount, 20.5);
      expect(purchase.details.single.promotion?.displayName, 'SALE');
      expect(purchase.deliveryType, 'delivery');
      expect(purchase.shippingCost, 12.5);
      expect(purchase.shipment?.address, 'Av. Siempre Viva 123');
      expect(purchase.shipment?.reference, 'Portón azul');
      expect(purchase.displayReceiptNumber, 'FAC-12');
      expect(purchase.successfulPayment?.method, 'tarjeta');
      expect(purchase.successfulPayment?.label, 'Tarjeta (Stripe)');
      expect(purchase.successfulPayment?.gateway, 'stripe');
      expect(formatPurchaseDate('2030-04-05T09:07:06'), contains('05/04/2030'));
      expect(formatPurchaseMoney(1234.5), '1.234,50');
    },
  );

  test('uses Spanish payment labels and safe fallbacks', () {
    expect(purchasePaymentMethod('pasarela'), 'Tarjeta / pasarela');
    expect(purchasePaymentMethod(null), 'No informado');
    expect(purchasePaymentStatus('exitoso'), 'aprobado');
    expect(purchasePaymentStatus(null), 'No informado');
    expect(formatPurchaseDate(null), '—');
  });

  test('defaults missing optional purchase fields without deriving money', () {
    final purchase = Purchase.fromJson({'id': 21, 'subtotal': 99.99});

    expect(purchase.deliveryType, 'sucursal');
    expect(purchase.shippingCost, isNull);
    expect(purchase.shipment, isNull);
    expect(purchase.details, isEmpty);
    expect(purchase.payments, isEmpty);
    expect(purchase.displayReceiptNumber, '#V-21');
    expect(purchase.total, 0);
  });

  test('parses the authenticated JSON receipt without calculating totals', () {
    final receipt = PurchaseReceipt.fromJson({
      'nro_comprobante': 'FAC-21',
      'fecha': '2030-04-05T09:07:06Z',
      'items': [
        {
          'descripcion': 'Pantalón de lino',
          'sku': 'PANT-21',
          'cantidad': 1,
          'precio_unitario': 120,
          'descuento': 25,
          'promocion': null,
          'subtotal': 95,
        },
      ],
      'subtotal': 120,
      'descuento': 25,
      'costo_envio': 8,
      'entrega': {'tipo_entrega': 'delivery', 'direccion': 'Calle 1'},
      'total': 103,
      'moneda': 'BOB',
      'pago': {
        'metodo': 'tarjeta',
        'monto': 103,
        'estado': 'exitoso',
        'referencia_externa': 'pay-21',
      },
    });

    expect(receipt.items.single.garment, 'Pantalón de lino');
    expect(receipt.items.single.finalPrice, 120);
    expect(receipt.items.single.subtotal, 95);
    expect(receipt.subtotal, 120);
    expect(receipt.discount, 25);
    expect(receipt.shippingCost, 8);
    expect(receipt.total, 103);
    expect(receipt.delivery?.address, 'Calle 1');
    expect(receipt.payment?.externalReference, 'pay-21');
  });
}
