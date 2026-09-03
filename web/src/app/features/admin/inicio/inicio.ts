import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { catchError, forkJoin, of } from 'rxjs';

import { API_URL } from '../../../core/api';
import { AuthService } from '../../../core/auth.service';

interface Ficha {
  etiqueta: string;
  total: number | null;
}

@Component({
  selector: 'app-admin-inicio',
  templateUrl: './inicio.html',
  styleUrl: './inicio.css',
})
export class AdminInicio {
  private http = inject(HttpClient);
  readonly sesion = inject(AuthService).sesion;

  readonly fichas = signal<Ficha[]>([]);
  readonly cargando = signal(true);

  private readonly recursos: Array<[string, string]> = [
    ['Categorias', 'admin/categorias'],
    ['Tallas', 'admin/tallas'],
    ['Colores', 'admin/colores'],
    ['Temporadas', 'admin/temporadas'],
    ['Colecciones', 'admin/colecciones'],
    ['Ciudades', 'admin/ciudades'],
    ['Sucursales', 'admin/sucursales'],
  ];

  constructor() {
    // `null` en un recurso significa "no se pudo leer" (permisos o API caida):
    // se muestra un guion en vez de romper todo el panel.
    forkJoin(
      this.recursos.map(([, ruta]) =>
        this.http.get<unknown[]>(`${API_URL}/${ruta}`).pipe(catchError(() => of(null))),
      ),
    ).subscribe((respuestas) => {
      this.fichas.set(
        this.recursos.map(([etiqueta], i) => ({ etiqueta, total: respuestas[i]?.length ?? null })),
      );
      this.cargando.set(false);
    });
  }
}
