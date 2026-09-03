import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_URL } from './api';

/** Una fila de cualquier catalogo: siempre trae id y el resto de columnas. */
export interface Registro {
  id: number;
  [campo: string]: unknown;
}

/** El backend responde a DELETE con un texto que explica que hizo. */
export interface RespuestaDetalle {
  detail: string;
}

/**
 * Cliente REST para los catalogos generados por `modules/comunes.py`.
 * Todos exponen el mismo contrato: GET "", POST "", PUT "/{id}", DELETE "/{id}".
 */
@Injectable({ providedIn: 'root' })
export class RecursoService {
  private http = inject(HttpClient);

  listar(ruta: string): Observable<Registro[]> {
    return this.http.get<Registro[]>(`${API_URL}/${ruta}`);
  }

  crear(ruta: string, datos: Record<string, unknown>): Observable<Registro> {
    return this.http.post<Registro>(`${API_URL}/${ruta}`, datos);
  }

  actualizar(ruta: string, id: number, datos: Record<string, unknown>): Observable<Registro> {
    return this.http.put<Registro>(`${API_URL}/${ruta}/${id}`, datos);
  }

  eliminar(ruta: string, id: number): Observable<RespuestaDetalle> {
    return this.http.delete<RespuestaDetalle>(`${API_URL}/${ruta}/${id}`);
  }
}
