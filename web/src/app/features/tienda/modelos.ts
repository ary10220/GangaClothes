/**
 * Tipos que comparten las pantallas de la tienda en linea: el carrito, el paso
 * de entrega del checkout (CU29) y el seguimiento del pedido.
 *
 * Son la forma exacta en que las devuelve el backend; donde se pueda, el nombre
 * del campo es el mismo que en `ventas/service.py` y `envios/service.py`.
 */

export interface LineaCarrito {
  id: number;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  cantidad: number;
  /** Precio de lista; `precio_final` ya trae la promocion vigente (CU18). */
  precio_unitario: number;
  precio_final: number;
  /** Descuento total de la linea. */
  descuento: number;
  promocion: { id: number; nombre: string; etiqueta: string } | null;
  subtotal: number;
  /** Solo en el carrito: lo que hay hoy en la sucursal de despacho. */
  disponible?: number;
  alcanza?: boolean;
}

/** El envio, resumido, tal como viaja dentro de la venta. */
export interface EnvioResumen {
  id: number;
  estado: 'pendiente' | 'asignado' | 'en_camino' | 'entregado' | 'cancelado';
  direccion: string;
  referencia: string | null;
  telefono_contacto: string | null;
  latitud: number;
  longitud: number;
  distancia_km: number;
  costo_envio: number;
  express: boolean;
  repartidor: string | null;
  fecha_estimada: string | null;
  fecha_entrega: string | null;
}

/** Carrito y venta en linea (backend: ventas/service.py `salida`). */
export interface VentaWeb {
  id: number;
  estado: 'carrito' | 'pendiente' | 'pagada' | 'anulada';
  sucursal_id: number;
  sucursal: string | null;
  unidades: number;
  subtotal: number;
  descuento: number;
  /** CU29: "sucursal" (retiro) o "delivery". Nulo en ventas viejas = retiro. */
  tipo_entrega: 'sucursal' | 'delivery';
  /** Lo que se cobra por el envio; ya esta sumado en `total`. */
  costo_envio: number;
  envio: EnvioResumen | null;
  total: number;
  nro_comprobante: string | null;
  detalle: LineaCarrito[];
}

/** Una linea del desglose del costo del envio, tal como la arma `tarifa.py`. */
export interface LineaDesglose {
  concepto: string;
  detalle: string;
  /** Negativo cuando es una bonificacion (el envio gratis por monto). */
  importe: number;
}

/** POST /api/envios/cotizar: lo que cuesta y cuanto tarda, sin crear nada. */
export interface CotizacionEnvio {
  distancia_km: number;
  express: boolean;
  dentro_de_cobertura: boolean;
  cobertura_km: number;
  desglose: LineaDesglose[];
  costo_envio: number;
  gratis: boolean;
  falta_para_envio_gratis: number;
  envio_gratis_desde: number;
  minutos_estimados: number;
  entrega_estimada: string | null;
  monto_compra: number;
  total_a_pagar: number;
  mensaje_cobertura: string | null;
  sucursal: {
    id: number;
    nombre: string;
    direccion: string | null;
    ciudad: string | null;
    latitud: number | null;
    longitud: number | null;
  } | null;
}
