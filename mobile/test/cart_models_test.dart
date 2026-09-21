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
    expect(cart.lines.single.finalPrice, 60.25);
    expect(cart.lines.single.hasPromotion, isFalse);
    expect(cart.deliveryType, 'sucursal');
    expect(cart.shippingCost, isNull);
    expect(formatCartMoney(1234.5), '1.234,50');
  });

  test('preserves active promotion and delivery values from the backend', () {
    final cart = Cart.fromJson({
      'id': 5,
      'estado': 'carrito',
      'sucursal_id': 2,
      'sucursal': 'Centro',
      'unidades': 1,
      'subtotal': 72.35,
      'descuento': 17.65,
      'tipo_entrega': 'delivery',
      'costo_envio': 6.5,
      'envio': {
        'direccion': 'Av. Siempre Viva 123',
        'referencia': 'Portón azul',
      },
      'total': 78.85,
      'detalle': [
        {
          'id': 9,
          'variante_id': 10,
          'sku': 'GC-10',
          'prenda': 'Pantalón',
          'talla': 'L',
          'color': 'Negro',
          'cantidad': 1,
          'precio_unitario': 90.0,
          'precio_final': 72.35,
          'descuento': 17.65,
          'promocion': {
            'id': 3,
            'nombre': 'Fin de temporada',
            'etiqueta': '30% OFF',
          },
          'subtotal': 72.35,
        },
      ],
    });

    final line = cart.lines.single;
    expect(line.unitPrice, 90.0);
    expect(line.finalPrice, 72.35);
    expect(line.discount, 17.65);
    expect(line.promotion?.displayName, '30% OFF');
    expect(cart.discount, 17.65);
    expect(cart.shippingCost, 6.5);
    expect(cart.shipment?.address, 'Av. Siempre Viva 123');
    expect(cart.total, 78.85);
  });

  test('keeps an explicit zero discount and renders no-promotion state', () {
    final cart = Cart.fromJson({
      'id': 6,
      'estado': 'carrito',
      'sucursal_id': 2,
      'unidades': 1,
      'subtotal': 40,
      'descuento': 0,
      'total': 40,
      'detalle': [
        {
          'id': 10,
          'variante_id': 11,
          'sku': 'GC-11',
          'prenda': 'Gorra',
          'talla': 'Única',
          'color': 'Roja',
          'cantidad': 1,
          'precio_unitario': 40,
          'descuento': 0,
          'promocion': null,
          'subtotal': 40,
        },
      ],
    });

    expect(cart.lines.single.finalPrice, 40);
    expect(cart.lines.single.discount, 0);
    expect(cart.lines.single.hasPromotion, isFalse);
    expect(cart.discount, 0);
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
