import { HttpClient } from '@angular/common/http';
import { Component, computed, effect, inject, signal, viewChild, ElementRef } from '@angular/core';

import { API_URL } from '../../core/api';
import { mensajeDeError } from '../../core/errores.interceptor';
import { SesionStore } from '../../core/sesion';
import { moneda } from '../formato';

/** Una prenda que el asistente nombro, para mostrarla como tarjeta. */
interface PrendaSugerida {
  id: number;
  nombre: string;
  precio: number;
  categoria: string | null;
  colores_disponibles: string[];
  tallas_disponibles: string[];
  promocion?: string;
  por_que_se_sugiere?: string;
}

/** POST /api/ia/chat */
interface RespuestaChat {
  conversacion_id: number;
  titulo: string | null;
  respuesta: string;
  modo: 'gemini' | 'sin_modelo';
  consultas: { herramienta: string; argumentos: Record<string, unknown> }[];
  prendas: PrendaSugerida[];
  aviso?: string;
}

interface Turno {
  de: 'yo' | 'asistente';
  texto: string;
  prendas?: PrendaSugerida[];
  /** Que consulto el asistente para responder: se puede desplegar. */
  consultas?: string[];
}

/**
 * Asistente de GangaClothes (CU28).
 *
 * Es el mismo componente para todos: lo que cambia es de que puede hablar, y eso
 * lo decide el backend segun el rol de quien tiene la sesion abierta. A un
 * cliente le busca ropa y le recomienda; al personal le contesta sobre ventas,
 * stock y ganancia.
 *
 * La pantalla no sabe nada de prendas ni de reportes: manda texto y muestra lo
 * que vuelve. Toda la logica (y la garantia de que no se inventa nada) esta en
 * el backend.
 */
@Component({
  selector: 'app-asistente',
  templateUrl: './asistente.html',
  styleUrl: './asistente.css',
  host: { '(document:keydown.escape)': 'cerrar()' },
})
export class Asistente {
  private http = inject(HttpClient);
  private sesion = inject(SesionStore);
  readonly moneda = moneda;

  private readonly caja = viewChild<ElementRef<HTMLDivElement>>('caja');

  readonly abierto = signal(false);
  readonly turnos = signal<Turno[]>([]);
  readonly borrador = signal('');
  readonly pensando = signal(false);
  readonly error = signal<string | null>(null);
  readonly detalleVisible = signal<number | null>(null);
  private conversacion: number | null = null;

  /** El personal ve el asistente en modo analista; el cliente, en modo vendedor. */
  readonly esPersonal = computed(() => this.sesion.tienePermiso('reportes:ver'));
  readonly visible = computed(
    () => this.sesion.autenticado() && (this.esPersonal() || this.sesion.tieneAlgunRol('cliente')),
  );

  readonly sugerencias = computed(() =>
    this.esPersonal()
      ? ['¿Cómo vienen las ventas este mes?', '¿Qué tengo que reponer?', '¿Qué prenda deja más ganancia?']
      : ['¿Qué me recomendás?', '¿Hay promociones?', 'Busco algo para una fiesta'],
  );

  constructor() {
    // Al desplegarse una respuesta nueva, la conversacion baja sola.
    effect(() => {
      this.turnos();
      queueMicrotask(() => {
        const caja = this.caja()?.nativeElement;
        if (caja) caja.scrollTop = caja.scrollHeight;
      });
    });
  }

  alternar(): void {
    this.abierto.update((v) => !v);
  }

  cerrar(): void {
    this.abierto.set(false);
  }

  usar(sugerencia: string): void {
    this.borrador.set(sugerencia);
    this.enviar();
  }

  enviar(): void {
    const texto = this.borrador().trim();
    if (!texto || this.pensando()) return;

    this.turnos.update((t) => [...t, { de: 'yo', texto }]);
    this.borrador.set('');
    this.error.set(null);
    this.pensando.set(true);

    this.http
      .post<RespuestaChat>(`${API_URL}/ia/chat`, {
        mensaje: texto,
        conversacion_id: this.conversacion,
        origen: 'web',
      })
      .subscribe({
        next: (r) => {
          this.pensando.set(false);
          this.conversacion = r.conversacion_id;
          this.turnos.update((t) => [
            ...t,
            {
              de: 'asistente',
              texto: r.respuesta,
              prendas: r.prendas,
              consultas: r.consultas.map((c) => c.herramienta),
            },
          ]);
          if (r.aviso) this.error.set(r.aviso);
        },
        error: (err) => {
          this.pensando.set(false);
          this.error.set(mensajeDeError(err, 'No se pudo consultar al asistente.'));
        },
      });
  }

  limpiar(): void {
    const id = this.conversacion;
    this.turnos.set([]);
    this.error.set(null);
    this.conversacion = null;
    // Se vacia tambien del lado del servidor; si falla, no importa: el hilo
    // nuevo ya arranca limpio igual.
    if (id !== null) this.http.delete(`${API_URL}/ia/conversaciones/${id}`).subscribe({ error: () => {} });
  }

  verDetalle(indice: number): void {
    this.detalleVisible.update((v) => (v === indice ? null : indice));
  }

  /** "buscar_prendas" -> "buscar prendas", para mostrarlo sin jerga. */
  nombreLegible(herramienta: string): string {
    return herramienta.replace(/_/g, ' ');
  }
}
