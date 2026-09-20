import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, input, output, signal, untracked } from '@angular/core';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { moneda } from '../../../shared/formato';
import { Coordenada, Mapa, PuntoMapa } from '../../../shared/mapa/mapa';
import { CotizacionEnvio, EnvioResumen, VentaWeb } from '../modelos';

const TELEFONO = /^[\d+\-\s]{6,20}$/;

/**
 * CU29: como quiere recibir el cliente su compra, dentro del carrito.
 *
 *   Retiro en sucursal  ->  no hay envio y el total es solo la mercaderia.
 *   Delivery            ->  marca su ubicacion en el mapa, ve el desglose del
 *                           costo y, al confirmar, el envio queda pedido y su
 *                           costo pasa a formar parte del total de la compra.
 *
 * El costo NUNCA lo calcula esta pantalla: se lo pide al backend
 * (`POST /api/envios/cotizar`), que es el unico que conoce la tarifa. Aqui solo
 * se muestra el desglose que el backend devuelve, renglon por renglon, para que
 * el cliente vea de donde sale cada boliviano antes de pagar.
 */
@Component({
  selector: 'app-selector-entrega',
  imports: [Mapa],
  templateUrl: './selector-entrega.html',
  styleUrl: './selector-entrega.css',
})
export class SelectorEntrega {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  readonly moneda = moneda;

  /** El carrito tal como lo devuelve la API (ventas/service.py `salida`). */
  readonly venta = input.required<VentaWeb>();
  readonly deshabilitado = input(false);

  /** El carrito recalculado que devuelve el backend al poner o quitar el envio. */
  readonly actualizado = output<VentaWeb>();

  readonly abierto = signal(false);
  readonly guardando = signal(false);
  readonly cotizando = signal(false);
  readonly error = signal<string | null>(null);
  readonly intento = signal(false);

  // ---- formulario ----
  readonly direccion = signal('');
  readonly referencia = signal('');
  readonly telefono = signal('');
  readonly express = signal(false);
  readonly punto = signal<Coordenada | null>(null);

  readonly cotizacion = signal<CotizacionEnvio | null>(null);

  readonly envio = computed<EnvioResumen | null>(() => this.venta().envio);
  readonly esDelivery = computed(() => this.venta().tipo_entrega === 'delivery' && !!this.envio());

  /** Sucursal de despacho: el punto del mapa desde el que sale el reparto. */
  readonly origen = computed<PuntoMapa | null>(() => {
    const suc = this.cotizacion()?.sucursal;
    if (!suc || suc.latitud === null || suc.longitud === null) return null;
    return {
      latitud: suc.latitud,
      longitud: suc.longitud,
      tipo: 'origen',
      titulo: suc.nombre,
      detalle: 'sale desde aqui',
    };
  });

  readonly puntos = computed<PuntoMapa[]>(() => {
    const lista: PuntoMapa[] = [];
    const origen = this.origen();
    if (origen) lista.push(origen);
    const destino = this.punto();
    if (destino) {
      lista.push({
        latitud: destino.latitud,
        longitud: destino.longitud,
        tipo: 'destino',
        titulo: this.direccion() || 'Tu direccion',
        detalle: this.referencia() || undefined,
      });
    }
    return lista;
  });

  readonly errores = computed(() => {
    const errores: Record<string, string> = {};
    if (this.direccion().trim().length < 5) errores['direccion'] = 'Escribe la calle y el numero.';
    if (!TELEFONO.test(this.telefono().trim())) errores['telefono'] = 'Un telefono de contacto valido.';
    if (!this.punto()) errores['punto'] = 'Marca en el mapa donde quieres recibir la compra.';
    return errores;
  });

  readonly fueraDeCobertura = computed(() => {
    const c = this.cotizacion();
    return !!c && !c.dentro_de_cobertura;
  });

  readonly puedeConfirmar = computed(
    () =>
      Object.keys(this.errores()).length === 0 &&
      !!this.cotizacion() &&
      !this.fueraDeCobertura() &&
      !this.guardando() &&
      !this.cotizando(),
  );

  constructor() {
    // Si el carrito ya viene con un envio (el cliente lo eligio antes, o volvio
    // de un pago rechazado), se pide su desglose para poder mostrarlo: el envio
    // guardado trae el costo, pero no de que partes se compone.
    effect(() => {
      const envio = this.envio();
      if (!envio) return;
      untracked(() => {
        if (this.cotizacion()?.costo_envio === envio.costo_envio && this.punto()) return;
        this.punto.set({ latitud: envio.latitud, longitud: envio.longitud });
        this.direccion.set(envio.direccion);
        this.referencia.set(envio.referencia ?? '');
        this.telefono.set(envio.telefono_contacto ?? '');
        this.express.set(envio.express);
        this.cotizar();
      });
    });
  }

  // ------------------------------------------------------------- eleccion
  elegirRetiro(): void {
    if (this.deshabilitado()) return;
    this.error.set(null);
    if (this.esDelivery()) this.quitarEnvio();
    else this.abierto.set(false);
  }

  elegirDelivery(): void {
    if (this.deshabilitado()) return;
    this.error.set(null);
    this.intento.set(false);
    this.abierto.set(true);
    if (!this.cotizacion()) this.cotizar();
  }

  cerrar(): void {
    this.abierto.set(false);
    this.intento.set(false);
  }

  // ------------------------------------------------------------ ubicacion
  marcar(coordenada: Coordenada): void {
    this.punto.set(coordenada);
    this.cotizar();
  }

  usarMiUbicacion(): void {
    if (!navigator.geolocation) {
      this.avisos.error('Tu navegador no puede darnos tu ubicacion. Marcala en el mapa.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (posicion) => this.marcar({ latitud: posicion.coords.latitude, longitud: posicion.coords.longitude }),
      () => this.avisos.error('No pudimos leer tu ubicacion. Marcala tocando el mapa.'),
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }

  cambiarExpress(valor: boolean): void {
    this.express.set(valor);
    this.cotizar();
  }

  /**
   * Le pregunta al backend cuanto sale el envio hasta el punto marcado. No crea
   * nada: se puede llamar todas las veces que el cliente mueva el marcador.
   */
  cotizar(): void {
    const destino = this.punto();
    if (!destino) return;
    this.cotizando.set(true);
    this.error.set(null);
    this.http
      .post<CotizacionEnvio>(`${API_URL}/envios/cotizar`, {
        latitud: destino.latitud,
        longitud: destino.longitud,
        sucursal_id: this.venta().sucursal_id,
        express: this.express(),
      })
      .subscribe({
        next: (cotizacion) => {
          this.cotizacion.set(cotizacion);
          this.cotizando.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.cotizando.set(false);
          this.cotizacion.set(null);
          this.error.set(mensajeDeError(err, 'No pudimos calcular el costo del envio.'));
        },
      });
  }

  // -------------------------------------------------------------- guardar
  confirmar(): void {
    this.intento.set(true);
    if (!this.puedeConfirmar()) return;
    const destino = this.punto()!;
    this.guardando.set(true);
    this.error.set(null);
    this.http
      .post<{ venta: VentaWeb; cotizacion: CotizacionEnvio }>(`${API_URL}/envios`, {
        venta_id: this.venta().id,
        direccion: this.direccion().trim(),
        referencia: this.referencia().trim() || null,
        telefono_contacto: this.telefono().trim(),
        latitud: destino.latitud,
        longitud: destino.longitud,
        express: this.express(),
      })
      .subscribe({
        next: (respuesta) => {
          this.guardando.set(false);
          this.abierto.set(false);
          this.intento.set(false);
          this.cotizacion.set(respuesta.cotizacion);
          this.actualizado.emit(respuesta.venta);
          const costo = respuesta.venta.costo_envio;
          this.avisos.ok(
            costo > 0
              ? `Envio a domicilio agregado por Bs ${moneda(costo)}.`
              : 'Envio a domicilio agregado, y te sale gratis por el monto de tu compra.',
          );
        },
        error: (err: HttpErrorResponse) => {
          this.guardando.set(false);
          this.error.set(mensajeDeError(err, 'No se pudo guardar la direccion de entrega.'));
        },
      });
  }

  private quitarEnvio(): void {
    const envio = this.envio();
    if (!envio) return;
    this.guardando.set(true);
    this.http.delete<VentaWeb>(`${API_URL}/envios/${envio.id}`).subscribe({
      next: (venta) => {
        this.guardando.set(false);
        this.abierto.set(false);
        this.cotizacion.set(null);
        this.actualizado.emit(venta);
        this.avisos.ok(`Retiras tu compra en ${venta.sucursal}.`);
      },
      error: (err: HttpErrorResponse) => {
        this.guardando.set(false);
        this.error.set(mensajeDeError(err, 'No se pudo volver a retiro en sucursal.'));
      },
    });
  }

  // --------------------------------------------------------- presentacion
  error_(campo: string): string | null {
    return this.intento() ? (this.errores()[campo] ?? null) : null;
  }

  /** 75 -> "1 h 15 min"; 40 -> "40 min". */
  duracion(minutos: number | undefined): string {
    if (!minutos) return '—';
    if (minutos < 60) return `${minutos} min`;
    const horas = Math.floor(minutos / 60);
    const resto = minutos % 60;
    return resto ? `${horas} h ${resto} min` : `${horas} h`;
  }

  /** El envio gratis se muestra como un ahorro, no como una linea negativa mas. */
  esAhorro(importe: number): boolean {
    return importe < 0;
  }
}
