import { PuntoMapa } from '../mapa/mapa';

/**
 * El envio a domicilio (CU29) tal como lo devuelve `GET /api/envios`, y las dos
 * cosas que las dos pantallas que lo muestran necesitan calcular igual: los
 * puntos del mapa y la linea de tiempo del pedido.
 *
 * Lo usan el seguimiento del cliente (`/mis-envios`) y el panel de la sucursal
 * (`/admin/envios`). Si el calculo estuviera repetido en cada una, tarde o
 * temprano dirian cosas distintas del mismo pedido.
 */
export type EstadoEnvio = 'pendiente' | 'asignado' | 'en_camino' | 'entregado' | 'cancelado';

export interface Envio {
  id: number;
  estado: EstadoEnvio;
  etiqueta_estado: string;
  /** true mientras el pedido sigue vivo (pendiente, asignado o en camino). */
  activo: boolean;
  direccion: string;
  latitud: number;
  longitud: number;
  referencia: string | null;
  telefono_contacto: string | null;
  distancia_km: number;
  costo_envio: number;
  express: boolean;
  repartidor: string | null;
  motivo_cancelacion: string | null;
  fecha_creacion: string | null;
  fecha_asignacion: string | null;
  fecha_salida: string | null;
  fecha_estimada: string | null;
  fecha_entrega: string | null;
  sucursal: {
    id: number;
    nombre: string;
    direccion: string | null;
    telefono: string | null;
    ciudad: string | null;
    latitud: number | null;
    longitud: number | null;
  } | null;
  cliente: { id: number; nombre: string | null; email: string | null; telefono: string | null } | null;
  venta: {
    id: number;
    estado: string;
    canal: string;
    fecha: string | null;
    nro_comprobante: string | null;
    subtotal: number;
    descuento: number;
    costo_envio: number;
    total: number;
  } | null;
  prendas: { id: number; sku: string; prenda: string; talla: string; color: string; cantidad: number }[];
  /** Con que se cobro la compra; `etiqueta` ya viene legible ("Tarjeta (Stripe)"). */
  pago: {
    metodo: string;
    pasarela: string | null;
    etiqueta: string;
    monto: number;
    referencia_externa: string | null;
    fecha: string | null;
  } | null;
}

/** Un paso de la linea de tiempo del pedido. */
export interface PasoEnvio {
  etiqueta: string;
  detalle: string | null;
  fecha: string | null;
  /** Ya ocurrio. */
  cumplido: boolean;
  /** Es el paso en el que esta el pedido ahora mismo. */
  actual: boolean;
}

/** El orden en que avanza un envio; `cancelado` sale de la via y va aparte. */
const AVANCE: EstadoEnvio[] = ['pendiente', 'asignado', 'en_camino', 'entregado'];

export function claseEstado(estado: EstadoEnvio): string {
  if (estado === 'entregado') return 'ok';
  if (estado === 'cancelado') return 'bajo';
  if (estado === 'en_camino') return 'rosa';
  return 'neutro';
}

/**
 * La linea de tiempo del pedido. Cada paso sabe si ya paso, si es el actual y
 * con que fecha ocurrio; las fechas salen de las que guarda el envio, no se
 * inventa ninguna.
 */
export function pasosDe(envio: Envio): PasoEnvio[] {
  const posicion = AVANCE.indexOf(envio.estado);
  const cancelado = envio.estado === 'cancelado';

  const pasos: PasoEnvio[] = [
    {
      etiqueta: 'Compra confirmada',
      detalle: envio.venta?.nro_comprobante ? `Comprobante ${envio.venta.nro_comprobante}` : 'Pago aprobado',
      fecha: envio.fecha_creacion,
      cumplido: true,
      actual: !cancelado && envio.estado === 'pendiente',
    },
    {
      etiqueta: 'Repartidor asignado',
      detalle: envio.repartidor,
      fecha: envio.fecha_asignacion,
      cumplido: !!envio.fecha_asignacion,
      actual: !cancelado && envio.estado === 'asignado',
    },
    {
      etiqueta: 'En camino',
      detalle: envio.repartidor ? `${envio.repartidor} salio con tu pedido` : null,
      fecha: envio.fecha_salida,
      cumplido: !!envio.fecha_salida,
      actual: !cancelado && envio.estado === 'en_camino',
    },
    {
      etiqueta: 'Entregado',
      detalle: envio.fecha_entrega ? envio.direccion : null,
      fecha: envio.fecha_entrega,
      cumplido: !!envio.fecha_entrega,
      actual: envio.estado === 'entregado',
    },
  ];

  if (cancelado) {
    // El pedido se salio de la via: los pasos que no ocurrieron ya no van a ocurrir.
    return [
      ...pasos.filter((p) => p.cumplido).map((p) => ({ ...p, actual: false })),
      {
        etiqueta: 'Cancelado',
        detalle: envio.motivo_cancelacion ?? 'La tienda cancelo la entrega a domicilio',
        fecha: null,
        cumplido: true,
        actual: true,
      },
    ];
  }
  // Los posteriores al estado actual quedan en gris, sin fecha.
  return pasos.map((paso, i) => ({ ...paso, cumplido: paso.cumplido || i <= posicion }));
}

/** Los dos puntos del recorrido: de que sucursal sale y a donde va. */
export function puntosDe(envio: Envio): PuntoMapa[] {
  const puntos: PuntoMapa[] = [];
  const origen = envio.sucursal;
  if (origen && origen.latitud !== null && origen.longitud !== null) {
    puntos.push({
      latitud: origen.latitud,
      longitud: origen.longitud,
      tipo: 'origen',
      titulo: origen.nombre,
      detalle: origen.direccion ?? undefined,
    });
  }
  puntos.push({
    latitud: envio.latitud,
    longitud: envio.longitud,
    tipo: 'destino',
    titulo: envio.direccion,
    detalle: envio.referencia ?? undefined,
  });
  return puntos;
}

/** 75 -> "1 h 15 min"; 40 -> "40 min". */
export function duracion(minutos: number | null | undefined): string {
  if (!minutos || minutos <= 0) return '—';
  if (minutos < 60) return `${minutos} min`;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto ? `${horas} h ${resto} min` : `${horas} h`;
}
