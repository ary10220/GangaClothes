import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, of, switchMap, throwError } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { Registro, RecursoService } from '../../../core/recurso.service';
import { SesionStore } from '../../../core/sesion';
import { moneda } from '../../../shared/formato';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';

interface LineaCarrito {
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

/** Carrito y venta en linea (backend: ventas/service.py `salida`). */
interface VentaWeb {
  id: number;
  estado: 'carrito' | 'pendiente' | 'pagada' | 'anulada';
  sucursal_id: number;
  sucursal: string | null;
  unidades: number;
  subtotal: number;
  descuento: number;
  total: number;
  nro_comprobante: string | null;
  detalle: LineaCarrito[];
}

/** POST /api/pagos: 201 si se aprobo; 402 con el mismo cuerpo si la pasarela rechazo. */
interface ResultadoPago {
  aprobado: boolean;
  motivo?: string;
  nro_comprobante?: string;
  pago: { referencia_externa: string | null };
  venta: VentaWeb;
}

const DIGITOS = /^\d{16}$/;
const VENCE = /^(0[1-9]|1[0-2])\/(\d{2})$/;
const CVC = /^\d{3,4}$/;

/**
 * CU17: carrito y compra con pasarela (Stripe en modo prueba, simulado).
 * Pagar son dos llamadas: confirmar el carrito (queda pendiente) y registrar el
 * pago. Si la pasarela rechaza, el backend devuelve la venta al carrito sin
 * tocar el inventario; si el cobro falla por otra razon, se reintenta sobre la
 * misma venta pendiente.
 */
@Component({
  selector: 'app-carrito',
  imports: [RouterLink, BarraTienda],
  templateUrl: './carrito.html',
  styleUrl: './carrito.css',
  host: { '(document:keydown.escape)': 'cerrarPago()' },
})
export class Carrito {
  private http = inject(HttpClient);
  private recursos = inject(RecursoService);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);
  readonly moneda = moneda;

  readonly carrito = signal<VentaWeb | null>(null);
  readonly sucursales = signal<Registro[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly ocupado = signal<number | 'sucursal' | null>(null);

  // ---- pago ----
  readonly pagoAbierto = signal(false);
  readonly numero = signal('');
  readonly titular = signal('');
  readonly vence = signal('');
  readonly cvc = signal('');
  readonly simularRechazo = signal(false);
  readonly intento = signal(false);
  readonly procesando = signal(false);
  readonly errorPago = signal<string | null>(null);
  readonly compra = signal<ResultadoPago | null>(null);
  /** Venta confirmada cuyo cobro no se completo: el reintento la reutiliza. */
  private ventaPendiente: VentaWeb | null = null;

  readonly faltantes = computed(() => (this.carrito()?.detalle ?? []).filter((l) => l.alcanza === false));

  readonly erroresTarjeta = computed(() => {
    const errores: Record<string, string> = {};
    if (!DIGITOS.test(this.numero().replace(/\s/g, ''))) errores['numero'] = 'El numero tiene 16 digitos.';
    if (!this.titular().trim()) errores['titular'] = 'Escribe el nombre como figura en la tarjeta.';
    const vence = VENCE.exec(this.vence().trim());
    if (!vence) errores['vence'] = 'Usa el formato MM/AA.';
    else {
      const fin = new Date(2000 + Number(vence[2]), Number(vence[1]), 1);
      if (fin.getTime() <= Date.now()) errores['vence'] = 'La tarjeta esta vencida.';
    }
    if (!CVC.test(this.cvc().trim())) errores['cvc'] = '3 o 4 digitos.';
    return errores;
  });

  constructor() {
    this.cargar();
    this.recursos.listar('admin/sucursales').subscribe({
      next: (filas) => this.sucursales.set(filas.filter((s) => s['activo'] !== false)),
      error: () => this.sucursales.set([]),
    });
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http
      .get<VentaWeb>(`${API_URL}/ventas/carrito`)
      .pipe(catchError((err: HttpErrorResponse) => (err.status === 404 ? of(null) : throwError(() => err))))
      .subscribe({
        next: (carrito) => {
          this.carrito.set(carrito);
          this.cargando.set(false);
        },
        error: (err) => {
          this.error.set(mensajeDeError(err, 'No se pudo cargar tu carrito.'));
          this.cargando.set(false);
        },
      });
  }

  // ------------------------------------------------------------- lineas
  cambiarSucursal(valor: string): void {
    this.ocupado.set('sucursal');
    this.http.post<VentaWeb>(`${API_URL}/ventas/carrito`, { sucursal_id: Number(valor) }).subscribe({
      next: (carrito) => this.actualizar(carrito),
      error: (err) => this.fallo(err, 'No se pudo cambiar la sucursal.'),
    });
  }

  cambiarCantidad(linea: LineaCarrito, cantidad: number): void {
    if (!Number.isInteger(cantidad) || cantidad < 1 || cantidad === linea.cantidad) return;
    this.ocupado.set(linea.id);
    this.http.put<VentaWeb>(`${API_URL}/ventas/carrito/items/${linea.id}`, { cantidad }).subscribe({
      next: (carrito) => this.actualizar(carrito),
      error: (err) => this.fallo(err, 'No se pudo cambiar la cantidad.'),
    });
  }

  quitar(linea: LineaCarrito): void {
    this.ocupado.set(linea.id);
    this.http.delete<VentaWeb>(`${API_URL}/ventas/carrito/items/${linea.id}`).subscribe({
      next: (carrito) => {
        this.actualizar(carrito);
        this.avisos.ok(`Quitaste ${linea.prenda} (${linea.talla} · ${linea.color}) del carrito.`);
      },
      error: (err) => this.fallo(err, 'No se pudo quitar la prenda.'),
    });
  }

  private actualizar(carrito: VentaWeb): void {
    this.ocupado.set(null);
    this.carrito.set(carrito);
  }

  private fallo(err: unknown, texto: string): void {
    this.ocupado.set(null);
    this.avisos.error(mensajeDeError(err, texto));
    this.cargar();
  }

  // --------------------------------------------------------------- pago
  abrirPago(): void {
    this.errorPago.set(null);
    this.intento.set(false);
    // Datos de la tarjeta de prueba de Stripe: no se cobra dinero real.
    if (!this.numero()) {
      this.numero.set('4242 4242 4242 4242');
      this.titular.set(this.sesion.nombreCompleto().toUpperCase());
      this.vence.set('12/30');
      this.cvc.set('123');
    }
    this.pagoAbierto.set(true);
  }

  cerrarPago(): void {
    if (!this.procesando()) this.pagoAbierto.set(false);
  }

  pagar(): void {
    this.intento.set(true);
    if (Object.keys(this.erroresTarjeta()).length > 0) return;

    this.procesando.set(true);
    this.errorPago.set(null);
    const confirmada = this.ventaPendiente
      ? of(this.ventaPendiente)
      : this.http.post<VentaWeb>(`${API_URL}/ventas/carrito/confirmar`, {});

    confirmada
      .pipe(
        switchMap((venta) => {
          this.ventaPendiente = venta;
          return this.http.post<ResultadoPago>(`${API_URL}/pagos`, {
            venta_id: venta.id,
            metodo: 'pasarela',
            monto: venta.total,
            simular_fallo: this.simularRechazo(),
          });
        }),
      )
      .subscribe({
        next: (resultado) => {
          this.procesando.set(false);
          this.ventaPendiente = null;
          this.pagoAbierto.set(false);
          this.carrito.set(null);
          this.compra.set(resultado);
          this.avisos.ok(`Pago aprobado. Comprobante ${resultado.nro_comprobante}.`);
        },
        error: (err: HttpErrorResponse) => {
          this.procesando.set(false);
          if (err.status === 402) {
            // Rechazo de la pasarela: la venta volvio al carrito y el stock no se toco.
            this.ventaPendiente = null;
            const motivo = String(err.error?.motivo ?? 'La pasarela rechazo el pago').replace(/\.?\s*$/, '.');
            this.errorPago.set(`${motivo} Tu carrito sigue intacto: puedes intentar de nuevo.`);
            this.cargar();
          } else if (this.ventaPendiente) {
            this.errorPago.set(
              `${mensajeDeError(err, 'No se pudo completar el pago.')} Tu compra quedo confirmada y pendiente de pago: ` +
                'puedes reintentar.',
            );
          } else {
            this.errorPago.set(mensajeDeError(err, 'No se pudo confirmar el carrito.'));
            this.cargar();
          }
        },
      });
  }

  seguirComprando(): void {
    this.compra.set(null);
    this.cargar();
  }

  error_(campo: string): string | null {
    return this.intento() ? (this.erroresTarjeta()[campo] ?? null) : null;
  }
}
