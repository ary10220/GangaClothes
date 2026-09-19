import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/cart/cart_models.dart';

void main() {
  test('parses cart lines, stock flags, totals, and receipt fields', () {
    final cart = Cart.fromJson({
      'id': 4,
      'estado': 'carrito',
      'sucursal_id': 2,
      'sucursal': 'Centro',
      'unidades': 2,
      'subtotal': 120.5,
      'descuento': 0,
      'total': 120.5,
      'detalle': [
        {
          'id': 8,
          'variante_id': 9,
          'sku': 'GC-09',
          'prenda': 'Camisa',
          'talla': 'M',
          'color': 'Azul',
          'cantidad': 2,
          'precio_unitario': 60.25,
          'subtotal': 120.5,
          'disponible': 1,
          'alcanza': false,
        },
      ],
    });

    expect(cart.lines.single.available, 1);
    expect(cart.hasInsufficientStock, isTrue);
    expect(formatCartMoney(1234.5), '1.234,50');
  });

  test('parses successful payment without card fields', () {
    final result = PaymentResult.fromJson({
      'aprobado': true,
      'nro_comprobante': 'C-000001',
      'pago': {'referencia_externa': 'pi_test_123'},
      'venta': {
        'id': 4,
        'estado': 'pagada',
        'sucursal_id': 2,
        'sucursal': 'Centro',
        'unidades': 1,
        'total': 40,
        'detalle': [],
      },
    });

    expect(result.approved, isTrue);
    expect(result.receiptNumber, 'C-000001');
    expect(result.externalReference, 'pi_test_123');
  });
}
