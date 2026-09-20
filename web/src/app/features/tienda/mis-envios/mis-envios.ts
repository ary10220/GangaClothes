import { HttpClient } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Envio, PasoEnvio, claseEstado, pasosDe, puntosDe } from '../../../shared/entrega/envio';
import { fechaCortaLocal, fechaLocal, instanteLocal, moneda } from '../../../shared/formato';
import { Mapa, PuntoMapa } from '../../../shared/mapa/mapa';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';

/** Cada cuanto se vuelve a preguntar por los pedidos que siguen en curso. */
const ESPERA = 15_000;

/**
 * CU29: seguimiento de mis pedidos a domicilio.
 *
 * Para cada envio muestra el mapa con la sucursal de origen y el destino, el
 * estado actual y la linea de tiempo con los pasos que ya ocurrieron y con qué
 * hora. Mientras haya un pedido en curso, la pantalla se refresca sola: asi el
 * cliente ve el cambio de estado sin recargar cuando la tienda lo despacha.
 */
@Component({
  selector: 'app-mis-envios',
  imports: [RouterLink, BarraTienda, Mapa],
  templateUrl: './mis-envios.html',
  styleUrl: './mis-envios.css',
})
export class MisEnvios {
  private http = inject(HttpClient);

  readonly fecha = fechaLocal;
  readonly moneda = moneda;
  readonly claseEstado = claseEstado;
  readonly pasos = pasosDe;
  readonly puntos = puntosDe;

  readonly envios = signal<Envio[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  /** Pedidos todavia vivos: son los que hacen que la pantalla siga consultando. */
  readonly enCurso = computed(() => this.envios().filter((e) => e.activo));

  constructor() {
    this.cargar();
    // Solo se consulta mientras haya algo en curso: un cliente sin pedidos
    // abiertos no tiene por que golpear la API cada quince segundos.
    const reloj = setInterval(() => {
      if (this.enCurso().length > 0) this.cargar(true);
    }, ESPERA);
    inject(DestroyRef).onDestroy(() => clearInterval(reloj));
  }

  cargar(silencioso = false): void {
    if (!silencioso) this.cargando.set(true);
    this.error.set(null);
    this.http.get<Envio[]>(`${API_URL}/envios/mios`).subscribe({
      next: (envios) => {
        this.envios.set(envios);
        this.cargando.set(false);
      },
      error: (err) => {
        this.cargando.set(false);
        if (!silencioso) this.error.set(mensajeDeError(err, 'No se pudieron cargar tus pedidos.'));
      },
    });
  }

  // ----------------------------------------------------------- presentacion
  mapa(envio: Envio): PuntoMapa[] {
    return puntosDe(envio);
  }

  linea(envio: Envio): PasoEnvio[] {
    return pasosDe(envio);
  }

  unidades(envio: Envio): number {
    return envio.prendas.reduce((suma, p) => suma + p.cantidad, 0);
  }

  /** Lo que se le dice al cliente sobre cuando llega, segun donde este el pedido. */
  promesa(envio: Envio): string {
    if (envio.estado === 'entregado') return `Entregado ${this.cuando(envio.fecha_entrega)}`;
    if (envio.estado === 'cancelado') return envio.motivo_cancelacion ?? 'La entrega a domicilio se cancelo';
    if (!envio.fecha_estimada) return 'Te avisamos apenas salga de la tienda';
    const cuando = this.cuando(envio.fecha_estimada);
    return envio.estado === 'en_camino' ? `Llega ${cuando}` : `Estimado ${cuando}`;
  }

  /** "hoy a las 18:42" o "el 21/09 a las 10:15": el dia solo si no es hoy. */
  private cuando(iso: string | null): string {
    const fecha = instanteLocal(iso);
    if (!fecha) return '';
    const hora = fecha.toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' });
    const esHoy = fecha.toDateString() === new Date().toDateString();
    return esHoy ? `hoy a las ${hora}` : `el ${fechaCortaLocal(iso)} a las ${hora}`;
  }
}
