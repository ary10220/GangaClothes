import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';

interface EventoBitacora {
  id: number;
  fecha: string | null;
  actor: string;
  modulo: string;
  accion: string;
  nivel: string;
  entidad: string | null;
  entidad_id: number | null;
  detalle: string | null;
  ip: string | null;
}

interface FiltrosDisponibles {
  modulos: string[];
  acciones: string[];
}

/**
 * Bitacora: quien hizo que y cuando. Las filas las escribe el backend en cada
 * operacion; desde aqui solo se consultan, nunca se editan ni se borran.
 */
@Component({
  selector: 'app-bitacora',
  templateUrl: './bitacora.html',
  styleUrl: './bitacora.css',
})
export class Bitacora {
  private http = inject(HttpClient);

  readonly eventos = signal<EventoBitacora[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly opciones = signal<FiltrosDisponibles>({ modulos: [], acciones: [] });

  // ---- filtros ----
  readonly modulo = signal('');
  readonly accion = signal('');
  readonly desde = signal('');
  readonly hasta = signal('');

  readonly hayFiltros = computed(
    () => this.modulo() !== '' || this.accion() !== '' || this.desde() !== '' || this.hasta() !== '',
  );

  constructor() {
    this.cargarOpciones();
    this.buscar();
  }

  private cargarOpciones(): void {
    this.http.get<FiltrosDisponibles>(`${API_URL}/seguridad/bitacora/filtros`).subscribe({
      next: (r) => this.opciones.set(r),
      error: () => this.opciones.set({ modulos: [], acciones: [] }),
    });
  }

  buscar(): void {
    this.cargando.set(true);
    this.error.set(null);

    let params = new HttpParams();
    const filtros: Record<string, string> = {
      modulo: this.modulo(),
      accion: this.accion(),
      desde: this.desde(),
      hasta: this.hasta(),
    };
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor) params = params.set(clave, valor);
    }

    this.http.get<EventoBitacora[]>(`${API_URL}/seguridad/bitacora`, { params }).subscribe({
      next: (filas) => {
        this.eventos.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        this.eventos.set([]);
        this.error.set(mensajeDeError(err, 'No se pudo cargar la bitacora.'));
        this.cargando.set(false);
      },
    });
  }

  limpiar(): void {
    this.modulo.set('');
    this.accion.set('');
    this.desde.set('');
    this.hasta.set('');
    this.buscar();
  }

  /** Los filtros de la propia tabla: tocar un modulo filtra por el. */
  filtrarPor(modulo: string): void {
    this.modulo.set(modulo);
    this.buscar();
  }

  fechaLegible(iso: string | null): string {
    if (!iso) return '—';
    const f = new Date(iso);
    if (Number.isNaN(f.getTime())) return iso;
    const dd = String(f.getDate()).padStart(2, '0');
    const mm = String(f.getMonth() + 1).padStart(2, '0');
    const hh = String(f.getHours()).padStart(2, '0');
    const mi = String(f.getMinutes()).padStart(2, '0');
    return `${dd}/${mm}/${f.getFullYear()} ${hh}:${mi}`;
  }

  /** El nombre va en negrita y el correo en gris, pero llega en un solo texto. */
  partesActor(actor: string): { nombre: string; correo: string | null } {
    const coincide = /^(.*?)\s*<(.+)>$/.exec(actor ?? '');
    return coincide ? { nombre: coincide[1], correo: coincide[2] } : { nombre: actor, correo: null };
  }

  claseNivel(nivel: string): string {
    if (nivel === 'ERROR') return 'bajo';
    if (nivel === 'ALERTA') return 'rosa';
    return 'ok';
  }
}
