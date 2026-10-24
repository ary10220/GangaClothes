import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, of, switchMap, throwError } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { Registro, RecursoService } from '../../../core/recurso.service';
import { SesionStore } from '../../../core/sesion';
import { Comprobantes } from '../../../shared/comprobante';
import { moneda } from '../../../shared/formato';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';
import { SelectorEntrega } from '../entrega/selector-entrega';
import { LineaCarrito, VentaWeb } from '../modelos';

/** GET /api/pagos/metodos?canal=web */
interface MetodoPago {
  valor: 'tarjeta' | 'qr';
  etiqueta: string;
  disponible: boolean;
  pasarela: string | null;
  detalle: string;
  modo?: string;
}

/** POST /api/pagos: 201 si se aprobo; 402 con el mismo cuerpo si la pasarela rechazo. */
interface ResultadoPago {
  aprobado: boolean;
  motivo?: string;
  nro_comprobante?: string;
  pago: { metodo: string; etiqueta: string; referencia_externa: string | null };
  venta: VentaWeb;
  tarjeta?: { marca: string | null; ultimos4: string | null; simulado: boolean };
}

/** POST /api/pagos/qr y GET /api/pagos/qr/{id} (backend: pasarelas/qr_bcp.py). */
interface CobroQr {
  qr_id: string;
  estado: string;
  descripcion: string;
  imagen_base64: string;
  monto: number;
  expira: string;
  simulado: boolean;
  pendiente: boolean;
  aprobado: boolean;
  rechazado: boolean;
  nro_comprobante?: string;
  motivo?: string;
  pago?: { referencia_externa: string | null; etiqueta: string };
  venta?: VentaWeb;
}

type Metodo = 'tarjeta' | 'qr';
type Paso = 'metodo' | 'tarjeta' | 'qr';

const DIGITOS = /^\d{16}$/;
const VENCE = /^(0[1-9]|1[0-2])\/(\d{2})$/;
const CVC = /^\d{3,4}$/;

/**
 * Algoritmo de Luhn: el digito verificador que llevan todas las tarjetas reales.
 * Es lo que hace cualquier formulario de pago antes de molestar a la pasarela, y
 * lo que evita que un numero cualquiera de 16 digitos parezca una tarjeta.
 */
function luhn(numero: string): boolean {
  let suma = 0;
  let doble = false;
  for (let i = numero.length - 1; i >= 0; i--) {
    let digito = Number(numero[i]);
    if (doble) {
      digito *= 2;
      if (digito > 9) digito -= 9;
    }
    suma += digito;
    doble = !doble;
  }
  return suma % 10 === 0;
}

/** Cada cuanto se le pregunta al banco si el QR ya se pago. */
const ESPERA_QR = 3000;

/**
 * CU17 (compra en linea) y CU29 (entrega): el carrito completo.
 *
 * Antes de pagar, el cliente elige como recibe la compra. Eso vive en
 * `<app-selector-entrega>`, que cuando el cliente confirma una direccion crea
 * el envio y devuelve el carrito ya recalculado: de ahi en adelante el total
 * que se muestra y el que cobra la pasarela son el mismo, con el envio dentro.
 *
 * Las dos pasarelas de pago:
 *
 *   tarjeta -> Stripe en modo prueba, se resuelve en la misma llamada.
 *   QR      -> Banco de Credito de Bolivia: se genera, el cliente lo escanea
 *              en su banca movil y esta pantalla pregunta cada pocos segundos
 *              como quedo.
 *
 * Pagar siempre son dos pasos: confirmar el carrito (la venta queda pendiente)
 * y cobrar. Si la pasarela rechaza, el backend devuelve la venta al carrito sin
 * tocar el inventario; si el cobro falla por otra razon, se reintenta sobre la
 * misma venta pendiente.
 */
@Component({
  selector: 'app-carrito',
  imports: [RouterLink, BarraTienda, SelectorEntrega],
  templateUrl: './carrito.html',
  styleUrl: './carrito.css',
  host: { '(document:keydown.escape)': 'cerrarPago()' },
})
export class Carrito implements OnDestroy {
  private http = inject(HttpClient);
  private recursos = inject(RecursoService);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);
  readonly comprobantes = inject(Comprobantes);
  readonly moneda = moneda;

  readonly carrito = signal<VentaWeb | null>(null);
  readonly sucursales = signal<Registro[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly ocupado = signal<number | 'sucursal' | null>(null);

  // ---- pago ----
  readonly pagoAbierto = signal(false);
  readonly paso = signal<Paso>('metodo');
  readonly metodos = signal<MetodoPago[]>([]);
  readonly metodo = signal<Metodo | null>(null);
  readonly procesando = signal(false);
  readonly errorPago = signal<string | null>(null);
  readonly compra = signal<ResultadoPago | null>(null);
  /** Venta confirmada cuyo cobro no se completo: el reintento la reutiliza. */
  private ventaPendiente: VentaWeb | null = null;

  // ---- tarjeta ----
  readonly numero = signal('');
  readonly titular = signal('');
  readonly vence = signal('');
  readonly cvc = signal('');
  readonly intento = signal(false);

  // ---- QR ----
  readonly qr = signal<CobroQr | null>(null);
  readonly esperandoQr = signal(false);
  private reloj: ReturnType<typeof setInterval> | null = null;

  readonly faltantes = computed(() => (this.carrito()?.detalle ?? []).filter((l) => l.alcanza === false));

  readonly erroresTarjeta = computed(() => {
    const errores: Record<string, string> = {};
    const numero = this.numero().replace(/\s/g, '');
    if (!DIGITOS.test(numero)) errores['numero'] = 'El numero tiene 16 digitos.';
    else if (!luhn(numero)) errores['numero'] = 'Ese numero de tarjeta no es valido.';
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
    // Que metodos ofrece hoy la tienda lo decide el backend segun sus variables
    // de entorno: si manana falta una clave, aqui deja de aparecer solo.
    this.http.get<{ metodos: MetodoPago[] }>(`${API_URL}/pagos/metodos?canal=web`).subscribe({
      next: (r) => this.metodos.set(r.metodos),
      error: () => this.metodos.set([]),
    });
  }

  ngOnDestroy(): void {
    this.detenerEspera();
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

  /**
   * El carrito que devuelve el selector de entrega ya viene con el costo del
   * envio sumado al total (CU29): se reemplaza tal cual, sin recalcular nada
   * en el navegador.
   */
  entregaCambiada(carrito: VentaWeb): void {
    this.carrito.set(carrito);
  }

  private fallo(err: unknown, texto: string): void {
    this.ocupado.set(null);
    this.avisos.error(mensajeDeError(err, texto));
    this.cargar();
  }

  // ------------------------------------------------------- abrir y cerrar
  abrirPago(): void {
    this.errorPago.set(null);
    this.intento.set(false);
    this.qr.set(null);
    const disponibles = this.metodos().filter((m) => m.disponible);
    // Con un solo metodo disponible no tiene sentido preguntar.
    if (disponibles.length === 1) this.elegir(disponibles[0].valor);
    else {
      this.metodo.set(null);
      this.paso.set('metodo');
    }
    this.pagoAbierto.set(true);
  }

  cerrarPago(): void {
    if (this.procesando()) return;
    this.detenerEspera();
    this.pagoAbierto.set(false);
  }

  elegir(metodo: Metodo): void {
    this.metodo.set(metodo);
    this.errorPago.set(null);
    if (metodo === 'tarjeta') {
      // Tarjeta de prueba de Stripe: no se cobra dinero real.
      if (!this.numero()) {
        this.numero.set('4242 4242 4242 4242');
        this.titular.set(this.sesion.nombreCompleto().toUpperCase());
        this.vence.set('12/30');
        this.cvc.set('123');
      }
      this.paso.set('tarjeta');
    } else {
      this.paso.set('qr');
      this.generarQr();
    }
  }

  volverAMetodos(): void {
    if (this.procesando()) return;
    this.detenerEspera();
    this.qr.set(null);
    this.errorPago.set(null);
    this.metodo.set(null);
    this.paso.set('metodo');
  }

  detalleMetodo(valor: Metodo): string {
    return this.metodos().find((m) => m.valor === valor)?.detalle ?? '';
  }

  /** La venta pendiente: se confirma el carrito una sola vez y se reusa al reintentar. */
  private confirmada() {
    return this.ventaPendiente
      ? of(this.ventaPendiente)
      : this.http.post<VentaWeb>(`${API_URL}/ventas/carrito/confirmar`, {});
  }

  // --------------------------------------------------------------- tarjeta
  pagar(): void {
    this.intento.set(true);
    if (Object.keys(this.erroresTarjeta()).length > 0) return;

    this.procesando.set(true);
    this.errorPago.set(null);
    this.confirmada()
      .pipe(
        switchMap((venta) => {
          this.ventaPendiente = venta;
          return this.http.post<ResultadoPago>(`${API_URL}/pagos`, {
            venta_id: venta.id,
            metodo: 'tarjeta',
            monto: venta.total,
            numero_tarjeta: this.numero(),
          });
        }),
      )
      .subscribe({
        next: (resultado) => this.cobrado(resultado),
        error: (err: HttpErrorResponse) => this.falloCobro(err),
      });
  }

  // -------------------------------------------------------------------- QR
  generarQr(): void {
    this.procesando.set(true);
    this.errorPago.set(null);
    this.confirmada()
      .pipe(
        switchMap((venta) => {
          this.ventaPendiente = venta;
          return this.http.post<CobroQr>(`${API_URL}/pagos/qr`, { venta_id: venta.id });
        }),
      )
      .subscribe({
        next: (cobro) => {
          this.procesando.set(false);
          this.qr.set(cobro);
          this.esperarPagoQr();
        },
        error: (err: HttpErrorResponse) => {
          this.procesando.set(false);
          this.errorPago.set(mensajeDeError(err, 'No se pudo generar el QR.'));
          if (!this.ventaPendiente) this.cargar();
        },
      });
  }

  /** Le pregunta al banco cada pocos segundos si el QR ya se pago. */
  private esperarPagoQr(): void {
    this.detenerEspera();
    this.esperandoQr.set(true);
    this.reloj = setInterval(() => this.consultarQr(), ESPERA_QR);
  }

  private detenerEspera(): void {
    if (this.reloj !== null) clearInterval(this.reloj);
    this.reloj = null;
    this.esperandoQr.set(false);
  }

  private consultarQr(): void {
    const cobro = this.qr();
    const venta = this.ventaPendiente;
    if (!cobro || !venta) return this.detenerEspera();

    this.http
      .get<CobroQr>(`${API_URL}/pagos/qr/${cobro.qr_id}?venta_id=${venta.id}`)
      .subscribe({
        next: (estado) => {
          this.qr.set({ ...cobro, ...estado });
          if (estado.aprobado) this.cobrado(estado as unknown as ResultadoPago);
        },
        error: (err: HttpErrorResponse) => {
          if (err.status === 402) this.rechazado(err.error?.motivo, 'El QR ya no es valido.');
          else if (err.status >= 500) {
            // Un corte pasajero no deberia cancelar el pago: se sigue preguntando.
            this.errorPago.set(mensajeDeError(err, 'No se pudo consultar el QR; reintentando…'));
          }
        },
      });
  }

  // ------------------------------------------------------ desenlaces comunes
  private cobrado(resultado: ResultadoPago): void {
    this.detenerEspera();
    this.procesando.set(false);
    this.ventaPendiente = null;
    this.pagoAbierto.set(false);
    this.carrito.set(null);
    this.qr.set(null);
    this.compra.set(resultado);
    this.avisos.ok(`Pago aprobado. Comprobante ${resultado.nro_comprobante}.`);
  }

  private rechazado(motivo: string | undefined, porDefecto: string): void {
    // La venta volvio al carrito y el stock no se toco.
    this.detenerEspera();
    this.procesando.set(false);
    this.ventaPendiente = null;
    this.qr.set(null);
    const texto = String(motivo ?? porDefecto).replace(/\.?\s*$/, '.');
    this.errorPago.set(`${texto} Tu carrito sigue intacto: puedes intentar de nuevo.`);
    this.paso.set('metodo');
    this.metodo.set(null);
    this.cargar();
  }

  private falloCobro(err: HttpErrorResponse): void {
    this.procesando.set(false);
    if (err.status === 402) {
      this.rechazado(err.error?.motivo, 'La pasarela rechazo el pago.');
    } else if (this.ventaPendiente) {
      this.errorPago.set(
        `${mensajeDeError(err, 'No se pudo completar el pago.')} Tu compra quedo confirmada y pendiente de pago: ` +
          'puedes reintentar.',
      );
    } else {
      this.errorPago.set(mensajeDeError(err, 'No se pudo confirmar el carrito.'));
      this.cargar();
    }
  }

  seguirComprando(): void {
    this.compra.set(null);
    this.cargar();
  }

  /**
   * "2026-09-19 20:20" -> "20:20". El banco manda la hora de Bolivia ya
   * calculada (asi la define su API), por eso se parte el texto en lugar de
   * construir un Date, que la reinterpretaria en la zona del navegador.
   */
  horaQr(expira: string): string {
    return expira?.split(' ')[1] ?? expira;
  }

  error_(campo: string): string | null {
    return this.intento() ? (this.erroresTarjeta()[campo] ?? null) : null;
  }
}
