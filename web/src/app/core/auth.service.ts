import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { API_URL } from './api';
import { rutaInicial } from './auth.guard';
import { SesionRespuesta, Usuario } from './modelos';
import { SesionStore } from './sesion';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  readonly sesion = inject(SesionStore);

  login(email: string, password: string): Observable<SesionRespuesta> {
    return this.http
      .post<SesionRespuesta>(`${API_URL}/auth/login`, { email, password })
      .pipe(tap((respuesta) => this.sesion.guardar(respuesta)));
  }

  registrar(datos: { nombre: string; apellido?: string; email: string; password: string; telefono?: string }) {
    return this.http
      .post<SesionRespuesta>(`${API_URL}/auth/register`, datos)
      .pipe(tap((respuesta) => this.sesion.guardar(respuesta)));
  }

  /** Revalida el token contra la API; util al recargar la pagina. */
  yo(): Observable<Usuario> {
    return this.http.get<Usuario>(`${API_URL}/auth/me`);
  }

  salir(): void {
    // Se avisa al backend para que el cierre quede en la bitacora, pero la
    // sesion local se limpia igual: si el token ya vencio, salir no debe fallar.
    const token = this.sesion.token;
    if (token) {
      this.http.post(`${API_URL}/auth/logout`, {}).subscribe({ error: () => {} });
    }
    this.sesion.limpiar();
    this.router.navigate(['/login']);
  }

  /** Ruta a la que corresponde entrar segun los roles de la sesion actual. */
  rutaInicial(): string {
    return rutaInicial(this.sesion.roles());
  }
}
