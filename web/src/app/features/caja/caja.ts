import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { Observable, catchError, of, switchMap } from 'rxjs';

import { API_URL } from '../../core/api';
import { mensajeDeError } from '../../core/errores.interceptor';
import { Notificaciones } from '../../core/notificaciones';
import { SesionStore } from '../../core/sesion';
import { SucursalActual } from '../../core/sucursal-actual';
import { OpcionFiltro, SelectorEstado } from '../../shared/estado/selector-estado';
import { fechaLocal, fechaSinZona, moneda } from '../../shared/formato';
import { SelectorSucursal } from '../../shared/sucursal/selector-sucursal';

type Metodo = 'efectivo' | 'tarjeta' | 'qr';

/** Lo que se usa de GET /api/catalogo. */
interface PrendaCatalogo {
  id: number;
  nombre: string;
  precio_venta: number;
  variantes: {
    id: number;
    sku: string;
    talla: string | null;
    color: string | null;
    disponibilidad: { sucursal_id: number; disponible: number }[];
  }[];
}

interface VarianteVenta {
  id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  precio: number;
  disponibilidad: { sucursal_id: number; disponible: number }[];
}

interface LineaCaja {
  variante: VarianteVenta;
  cantidad: number;
}

/** Lo que se usa de GET /api/reservas?estado=preparada. */
interface ReservaPreparada {
  id: number;
  fecha_hora_prueba: string | null;
  unidades: number;
  cliente: { nombre: string | null };
  detalle: { variante_id: number; sku: string; cantidad: number; estado: 'reservado' | 'liberado' }[];
}

/** POST /api/ventas/presencial (backend: ventas/service.py `salida`). */
interface VentaCaja {
  id: number;
  total: number;
  subtotal: number;
  descuento: number;
  sucursal: string | null;
  reserva_id: number | null;
  cajero: { nombre: string } | null;
  cliente: { nombre: string | null } | null;
  detalle: { sku: string; prenda: string; talla: string; color: string; cantidad: number; precio_unitario: number; subtotal: number }[];
}

/** POST /api/pagos cuando el cobro sale bien. */
interface ResultadoPago {
  nro_comprobante: string;
  cambio: number;
  reserva_atendida: boolean;
  movimientos: { cantidad: number }[];
  pago: { fecha: string | null };
  venta: VentaCaja;
}

/** GET /api/ventas/{id}/comprobante. */
interface Comprobante {
  nro_comprobante: string;
  fecha: string | null;
  sucursal: { nombre: string; direccion: string | null } | null;
  venta_id: number;
  reserva_id: number | null;
  cajero: { nombre: string } | null;
  cliente: { nombre: string | null } | null;
  items: { descripcion: string; sku: string; cantidad: number; precio_unitario: number; subtotal: number }[];
  subtotal: number;
  descuento: number;
  total: number;
  pago: { metodo: string | null; recibido: number; cambio: number };
}

interface Cobro {
  comprobante: Comprobante;
  unidades: number;
  reservaAtendida: number | null;
}

const METODOS: OpcionFiltro<Metodo>[] = [
  { valor: 'efectivo', etiqueta: 'Efectivo' },
  { valor: 'tarjeta', etiqueta: 'Tarjeta' },
  { valor: 'qr', etiqueta: 'QR' },
];

const MONTO = /^\d+([.,]\d{1,2})?$/;
const centavos = (n: number) => Math.round(n * 100) / 100;

/**
 * CU14 venta presencial y CU15 cobro en caja.
 * Cobrar son dos pasos del backend: crear la venta pendiente y registrar el
 * pago, que es el que descuenta el inventario. Si el pago falla, la misma venta
 * se reutiliza en el siguiente intento mientras no cambien las lineas.
 */
@Component({
  selector: 'app-caja',
  imports: [SelectorEstado, SelectorSucursal],
  templateUrl: './caja.html',
  styleUrl: './caja.css',
})
export class Caja {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  readonly sesion = inject(SesionStore);
  readonly sucursal = inject(SucursalActual);

  readonly metodos = METODOS;
  readonly moneda = moneda;
  readonly fechaCita = fechaSinZona;
  readonly fechaCobro = fechaLocal;

  // ---- catalogo y reservas ----
  readonly catalogo = signal<VarianteVenta[]>([]);
  readonly cargandoCatalogo = signal(false);
  readonly errorCatalogo = signal<string | null>(null);
  readonly reservas = signal<ReservaPreparada[]>([]);
  readonly cargandoReservas = signal(false);

  // ---- venta en curso ----
  readonly busqueda = signal('');
  readonly lineas = signal<LineaCaja[]>([]);
  readonly reservaCargada = signal<ReservaPreparada | null>(null);
  readonly metodo = signal<Metodo>('efectivo');
  readonly recibido = signal('');

  // ---- cobro ----
  readonly cobrando = signal(false);
  readonly errorCobro = signal<{ titulo: string; detalle: string } | null>(null);
  readonly cobro = signal<Cobro | null>(null);
  private ventaPendiente: { firma: string; venta: VentaCaja } | null = null;

  readonly resultados = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    if (!texto) return [];
    return this.catalogo()
      .filter((v) => `${v.sku} ${v.prenda} ${v.talla} ${v.color}`.toLowerCase().includes(texto))
      .slice(0, 8);
  });

  readonly total = computed(() => centavos(this.lineas().reduce((s, l) => s + l.variante.precio * l.cantidad, 0)));
  readonly unidades = computed(() => this.lineas().reduce((s, l) => s + l.cantidad, 0));
  readonly hayExcesos = computed(() => this.lineas().some((l) => this.excede(l)));

  readonly montoRecibido = computed(() => {
    const texto = this.recibido().trim();
    return MONTO.test(texto) ? Number(texto.replace(',', '.')) : null;
  });

  readonly errorMonto = computed<string | null>(() => {
    if (this.metodo() !== 'efectivo' || this.lineas().length === 0) return null;
    const texto = this.recibido().trim();
    if (texto === '') return null;
    const monto = this.montoRecibido();
    if (monto === null) return 'Ingresa el monto con hasta 2 decimales.';
    if (monto < this.total()) return `Monto insuficiente: faltan Bs ${moneda(this.total() - monto)}.`;
    return null;
  });

  readonly cambio = computed(() => {
    const monto = this.montoRecibido();
    return this.metodo() === 'efectivo' && monto !== null && monto >= this.total() ? centavos(monto - this.total()) : null;
  });

  readonly bloqueo = computed<string | null>(() => {
    if (this.lineas().length === 0) return 'Agrega prendas a la venta.';
    if (this.hayExcesos()) return 'Hay lineas con mas unidades de las que hay en la sucursal.';
    if (this.metodo() === 'efectivo' && this.recibido().trim() === '') return 'Ingresa el monto que entrega el cliente.';
    return this.errorMonto();
  });

  constructor() {
    this.cargarCatalogo();
    effect(() => {
      const id = this.sucursal.id();
      untracked(() => {
        this.nuevaVenta();
        this.cargarReservas(id);
      });
    });
    effect(() => {
      this.metodo();
      untracked(() => this.errorCobro.set(null));
    });
  }

  // ------------------------------------------------------------------ carga
  cargarCatalogo(): void {
    this.cargandoCatalogo.set(true);
    this.errorCatalogo.set(null);
    this.http.get<PrendaCatalogo[]>(`${API_URL}/catalogo`).subscribe({
      next: (prendas) => {
        const variantes = prendas.flatMap((p) =>
          p.variantes.map((v) => ({
            id: v.id,
            sku: v.sku,
            prenda: p.nombre,
            talla: v.talla ?? '—',
            color: v.color ?? '—',
            precio: Number(p.precio_venta),
            disponibilidad: v.disponibilidad,
          })),
        );
        this.catalogo.set(variantes);
        // Las lineas guardan su variante: se refrescan con el stock nuevo.
        const porId = new Map(variantes.map((v) => [v.id, v]));
        this.lineas.update((lineas) => lineas.map((l) => ({ ...l, variante: porId.get(l.variante.id) ?? l.variante })));
        this.cargandoCatalogo.set(false);
      },
      error: (err) => {
        this.errorCatalogo.set(mensajeDeError(err, 'No se pudo cargar el catalogo de prendas.'));
        this.cargandoCatalogo.set(false);
      },
    });
  }

  cargarReservas(sucursalId: number | null = this.sucursal.id()): void {
    if (sucursalId === null) {
      this.reservas.set([]);
      return;
    }
    this.cargandoReservas.set(true);
    this.http
      .get<ReservaPreparada[]>(`${API_URL}/reservas`, { params: { sucursal_id: sucursalId, estado: 'preparada' } })
      .subscribe({
        next: (filas) => {
          this.reservas.set(filas);
          this.cargandoReservas.set(false);
        },
        error: () => {
          this.reservas.set([]);
          this.cargandoReservas.set(false);
        },
      });
  }

  // ---------------------------------------------------------------- lineas
  agregar(variante: VarianteVenta): void {
    if (this.cobro()) this.nuevaVenta();
    this.lineas.update((lineas) => {
      const existente = lineas.findIndex((l) => l.variante.id === variante.id);
      if (existente === -1) return [...lineas, { variante, cantidad: 1 }];
      return lineas.map((l, i) => (i === existente ? { ...l, cantidad: l.cantidad + 1 } : l));
    });
    this.busqueda.set('');
    this.errorCobro.set(null);
  }

  /** Enter en el buscador: el SKU exacto (lo que entrega un lector de codigos) o el primer resultado. */
  agregarDesdeBuscador(): void {
    const texto = this.busqueda().trim().toLowerCase();
    const exacta = this.catalogo().find((v) => v.sku.toLowerCase() === texto);
    const elegida = exacta ?? this.resultados()[0];
    if (elegida) this.agregar(elegida);
  }

  cambiarCantidad(indice: number, evento: Event): void {
    const input = evento.target as HTMLInputElement;
    const cantidad = Number(input.value);
    if (!Number.isInteger(cantidad) || cantidad < 1) {
      input.value = String(this.lineas()[indice].cantidad);
      return;
    }
    this.lineas.update((lineas) => lineas.map((l, i) => (i === indice ? { ...l, cantidad } : l)));
    this.errorCobro.set(null);
  }

  quitar(indice: number): void {
    this.lineas.update((lineas) => lineas.filter((_l, i) => i !== indice));
    if (this.lineas().length === 0) this.reservaCargada.set(null);
    this.errorCobro.set(null);
  }

  cargarReserva(reserva: ReservaPreparada): void {
    if (this.cobro()) this.nuevaVenta();
    const porId = new Map(this.catalogo().map((v) => [v.id, v]));
    const retenidas = reserva.detalle.filter((d) => d.estado === 'reservado');
    const faltan = retenidas.filter((d) => !porId.has(d.variante_id)).map((d) => d.sku);
    this.lineas.set(
      retenidas.filter((d) => porId.has(d.variante_id)).map((d) => ({ variante: porId.get(d.variante_id)!, cantidad: d.cantidad })),
    );
    this.reservaCargada.set(reserva);
    this.errorCobro.set(null);
    if (faltan.length) this.avisos.error(`Estas prendas de la reserva ya no estan a la venta: ${faltan.join(', ')}.`);
  }

  quitarReserva(): void {
    this.reservaCargada.set(null);
    this.lineas.set([]);
    this.errorCobro.set(null);
  }

  // ------------------------------------------------------------------ cobro
  cobrar(): void {
    const sucursalId = this.sucursal.id();
    if (this.bloqueo() || this.cobrando() || sucursalId === null) return;

    const firma = this.firma();
    const metodo = this.metodo();
    const recibido = this.montoRecibido();
    const nombreSucursal = this.sucursal.actual()?.nombre ?? 'la sucursal';
    this.cobrando.set(true);
    this.errorCobro.set(null);

    const venta$: Observable<VentaCaja> =
      this.ventaPendiente?.firma === firma
        ? of(this.ventaPendiente.venta)
        : this.http.post<VentaCaja>(`${API_URL}/ventas/presencial`, {
            sucursal_id: sucursalId,
            reserva_id: this.reservaCargada()?.id ?? null,
            detalle: this.lineas().map((l) => ({ variante_id: l.variante.id, cantidad: l.cantidad })),
          });

    let resultado: ResultadoPago;
    venta$
      .pipe(
        switchMap((venta) => {
          this.ventaPendiente = { firma, venta };
          // En tarjeta y QR se cobra el total de la venta que armo el backend.
          const monto = metodo === 'efectivo' ? recibido : venta.total;
          return this.http.post<ResultadoPago>(`${API_URL}/pagos`, { venta_id: venta.id, metodo, monto });
        }),
        switchMap((r) => {
          resultado = r;
          // El cobro ya se hizo: si el ticket no llega, se arma con la respuesta del pago.
          return this.http
            .get<Comprobante>(`${API_URL}/ventas/${r.venta.id}/comprobante`)
            .pipe(catchError(() => of(null)));
        }),
      )
      .subscribe({
        next: (comprobante) => {
          this.cobrando.set(false);
          this.ventaPendiente = null;
          const unidades = resultado.movimientos.reduce((s, m) => s + m.cantidad, 0);
          this.cobro.set({
            comprobante: comprobante ?? this.comprobanteDesde(resultado, metodo, recibido),
            unidades,
            reservaAtendida: resultado.reserva_atendida ? resultado.venta.reserva_id : null,
          });
          this.avisos.ok(
            `Cobro registrado · comprobante ${resultado.nro_comprobante}. ` +
              (unidades === 1 ? 'Se desconto 1 unidad' : `Se descontaron ${unidades} unidades`) +
              ` del inventario de ${nombreSucursal}.`,
          );
          this.cargarCatalogo();
          this.cargarReservas();
        },
        error: (err: HttpErrorResponse) => {
          this.cobrando.set(false);
          const detalle = mensajeDeError(err, 'No se pudo completar el cobro.');
          this.errorCobro.set({ titulo: this.tituloError(detalle), detalle });
          if (/ya esta pagada/i.test(detalle)) this.ventaPendiente = null;
          if (/stock|unidades libres/i.test(detalle)) this.cargarCatalogo();
        },
      });
  }

  nuevaVenta(): void {
    this.lineas.set([]);
    this.reservaCargada.set(null);
    this.busqueda.set('');
    this.metodo.set('efectivo');
    this.recibido.set('');
    this.errorCobro.set(null);
    this.cobro.set(null);
    this.ventaPendiente = null;
  }

  /** Identifica la venta armada: si no cambio, se reintenta el pago sobre la misma venta. */
  private firma(): string {
    return JSON.stringify({
      sucursal: this.sucursal.id(),
      reserva: this.reservaCargada()?.id ?? null,
      lineas: this.lineas().map((l) => [l.variante.id, l.cantidad]),
    });
  }

  private tituloError(detalle: string): string {
    if (/no cubre el total/i.test(detalle)) return 'Monto insuficiente';
    if (/total exacto/i.test(detalle)) return 'Monto incorrecto';
    if (/ya esta pagada/i.test(detalle)) return 'Esta venta ya fue cobrada';
    if (/reserva ya esta en la venta/i.test(detalle)) return 'La reserva ya tiene una venta abierta';
    if (/stock|unidades libres/i.test(detalle)) return 'Stock insuficiente';
    return 'No se pudo cobrar';
  }

  private comprobanteDesde(r: ResultadoPago, metodo: Metodo, recibido: number | null): Comprobante {
    const total = r.venta.total;
    return {
      nro_comprobante: r.nro_comprobante,
      fecha: r.pago.fecha,
      sucursal: r.venta.sucursal ? { nombre: r.venta.sucursal, direccion: null } : null,
      venta_id: r.venta.id,
      reserva_id: r.venta.reserva_id,
      cajero: r.venta.cajero,
      cliente: r.venta.cliente,
      items: r.venta.detalle.map((i) => ({
        descripcion: `${i.prenda} ${i.talla}/${i.color}`,
        sku: i.sku,
        cantidad: i.cantidad,
        precio_unitario: i.precio_unitario,
        subtotal: i.subtotal,
      })),
      subtotal: r.venta.subtotal,
      descuento: r.venta.descuento,
      total,
      pago: { metodo, recibido: metodo === 'efectivo' ? (recibido ?? total) : total, cambio: r.cambio },
    };
  }

  // ----------------------------------------------------------- presentacion
  disponible(variante: VarianteVenta): number {
    return variante.disponibilidad.find((d) => d.sucursal_id === this.sucursal.id())?.disponible ?? 0;
  }

  /** Lo que la reserva cargada aparta de esa variante: tambien se puede vender. */
  retenido(varianteId: number): number {
    return (this.reservaCargada()?.detalle ?? [])
      .filter((d) => d.variante_id === varianteId && d.estado === 'reservado')
      .reduce((s, d) => s + d.cantidad, 0);
  }

  limite(variante: VarianteVenta): number {
    return this.disponible(variante) + this.retenido(variante.id);
  }

  excede(linea: LineaCaja): boolean {
    return linea.cantidad > this.limite(linea.variante);
  }

  subtotal(linea: LineaCaja): number {
    return centavos(linea.variante.precio * linea.cantidad);
  }

  etiquetaMetodo(metodo: string | null): string {
    return METODOS.find((m) => m.valor === metodo)?.etiqueta ?? metodo ?? '—';
  }
}
