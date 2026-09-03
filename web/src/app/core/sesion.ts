import { Injectable, computed, signal } from '@angular/core';

import { Rol, SesionRespuesta, Usuario } from './modelos';

const CLAVE_TOKEN = 'gc_token';
const CLAVE_USUARIO = 'gc_usuario';

/**
 * Guarda el token y el usuario en localStorage y los expone como signals.
 * No depende de HttpClient a proposito: los interceptores lo inyectan y
 * hacerlo al reves crearia una dependencia circular con HttpClient.
 */
@Injectable({ providedIn: 'root' })
export class SesionStore {
  private readonly _usuario = signal<Usuario | null>(this.leerUsuario());

  readonly usuario = this._usuario.asReadonly();
  readonly autenticado = computed(() => this._usuario() !== null);
  readonly roles = computed<Rol[]>(() => this._usuario()?.roles ?? []);
  readonly nombreCompleto = computed(() => {
    const u = this._usuario();
    return u ? [u.nombre, u.apellido].filter(Boolean).join(' ') : '';
  });
  /** El rol de mayor jerarquia, para mostrarlo en la barra superior. */
  readonly rolPrincipal = computed<Rol | null>(() => {
    const jerarquia: Rol[] = ['administrador', 'encargado', 'cajero', 'cliente'];
    return jerarquia.find((r) => this.roles().includes(r)) ?? null;
  });

  get token(): string | null {
    return localStorage.getItem(CLAVE_TOKEN);
  }

  guardar(sesion: SesionRespuesta): void {
    localStorage.setItem(CLAVE_TOKEN, sesion.access_token);
    localStorage.setItem(CLAVE_USUARIO, JSON.stringify(sesion.usuario));
    this._usuario.set(sesion.usuario);
  }

  limpiar(): void {
    localStorage.removeItem(CLAVE_TOKEN);
    localStorage.removeItem(CLAVE_USUARIO);
    this._usuario.set(null);
  }

  tieneAlgunRol(...roles: Rol[]): boolean {
    return roles.some((r) => this.roles().includes(r));
  }

  private leerUsuario(): Usuario | null {
    const crudo = localStorage.getItem(CLAVE_USUARIO);
    if (!crudo || !localStorage.getItem(CLAVE_TOKEN)) return null;
    try {
      return JSON.parse(crudo) as Usuario;
    } catch {
      // localStorage corrupto: se descarta la sesion en lugar de romper el arranque.
      localStorage.removeItem(CLAVE_USUARIO);
      return null;
    }
  }
}
