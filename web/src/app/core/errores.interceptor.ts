import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { API_URL } from './api';
import { Notificaciones } from './notificaciones';
import { SesionStore } from './sesion';

/** Devuelve el `detail` de FastAPI si viene, o un texto por defecto. */
export function mensajeDeError(error: unknown, porDefecto: string): string {
  if (!(error instanceof HttpErrorResponse)) return porDefecto;
  const detalle = error.error?.detail;
  if (typeof detalle === 'string') return detalle;
  // 422 de Pydantic: detail es una lista de {loc, msg}.
  if (Array.isArray(detalle)) {
    return detalle.map((d) => `${d.loc?.at(-1) ?? ''}: ${d.msg}`).join(' · ') || porDefecto;
  }
  return porDefecto;
}

/**
 * Traduce los errores de la API a avisos legibles.
 * El 401 en /auth/login NO se toca: ahi significa "credenciales incorrectas"
 * y lo muestra la propia pantalla de login, no un aviso global.
 */
export const erroresInterceptor: HttpInterceptorFn = (req, next) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  const avisos = inject(Notificaciones);
  const esAuth = req.url.startsWith(`${API_URL}/auth/`);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 0) {
        avisos.error('No se pudo contactar al servidor. Verifica que la API este corriendo en ' + API_URL);
      } else if (error.status === 401 && !esAuth) {
        sesion.limpiar();
        avisos.error('Tu sesion expiro o no es valida. Inicia sesion nuevamente.');
        router.navigate(['/login'], { queryParams: { volverA: router.url } });
      } else if (error.status === 403) {
        avisos.error(mensajeDeError(error, 'No tienes permisos para realizar esta operacion.'));
      } else if (error.status >= 500) {
        avisos.error('Error interno del servidor. Intenta de nuevo en un momento.');
      }
      return throwError(() => error);
    }),
  );
};
