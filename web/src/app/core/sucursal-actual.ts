import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';

import { API_URL } from './api';
import { mensajeDeError } from './errores.interceptor';
import { SesionStore } from './sesion';

export interface Sucursal {
  id: number;
  nombre: string;
  ciudad_id: number;
  activo: boolean | null;
}

const CLAVE_SUCURSAL = 'gc_sucursal';

/**
 * Sucursal con la que trabajan las pantallas de operacion (inventario,
 * movimientos, compras y reservas). Es una sola para todas: la que se elige en
 * una pantalla queda elegida en las demas.
 *
 * Al cargar se preselecciona, en este orden: la sucursal asignada al usuario,
 * la ultima elegida en este navegador y la primera sucursal activa.
 */
@Injectable({ providedIn: 'root' })
export class SucursalActual {
  private http = inject(HttpClient);
  private sesion = inject(SesionStore);

  readonly sucursales = signal<Sucursal[]>([]);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly id = signal<number | null>(null);

  readonly actual = computed(() => this.sucursales().find((s) => s.id === this.id()) ?? null);
  readonly asignadaId = computed(() => this.sesion.usuario()?.sucursal_id ?? null);

  /** Usuario para el que se cargo la lista: si cambia la sesion, se vuelve a preseleccionar. */
  private cargadaPara: number | null = null;

  /** Cada pantalla la llama al abrir; solo la primera va al servidor. */
  cargar(): void {
    const usuarioId = this.sesion.usuario()?.id ?? null;
    if (this.cargando() || (this.cargadaPara !== null && this.cargadaPara === usuarioId)) return;

    this.cargando.set(true);
    this.error.set(null);
    this.http.get<Sucursal[]>(`${API_URL}/admin/sucursales`).subscribe({
      next: (filas) => {
        const activas = filas.filter((s) => s.activo !== false);
        this.sucursales.set(activas);
        this.id.set(this.preseleccion(activas));
        this.cargadaPara = usuarioId;
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar las sucursales.'));
        this.cargando.set(false);
      },
    });
  }

  elegir(id: number): void {
    this.id.set(id);
    localStorage.setItem(CLAVE_SUCURSAL, String(id));
  }

  private preseleccion(activas: Sucursal[]): number | null {
    const existe = (id: number | null) => id !== null && activas.some((s) => s.id === id);
    const asignada = this.asignadaId();
    if (existe(asignada)) return asignada;
    const guardada = Number(localStorage.getItem(CLAVE_SUCURSAL));
    if (existe(guardada)) return guardada;
    return activas[0]?.id ?? null;
  }
}
