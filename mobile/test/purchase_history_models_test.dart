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
          },
        ],
      });

      expect(purchase.id, 12);
      expect(purchase.customer?.email, 'c@example.com');
      expect(purchase.details.single.garment, 'Camisa');
      expect(purchase.details.single.subtotal, 180.5);
      expect(purchase.successfulPayment?.method, 'tarjeta');
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
}
