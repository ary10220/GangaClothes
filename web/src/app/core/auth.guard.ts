import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { Notificaciones } from './notificaciones';
import { SesionStore } from './sesion';

/** Ruta inicial segun el rol: el personal va al panel, el cliente al catalogo. */
export function rutaInicial(roles: string[]): string {
  const esPersonal = ['administrador', 'encargado', 'cajero'].some((r) => roles.includes(r));
  return esPersonal ? '/admin' : '/catalogo';
}

/** Exige sesion iniciada. Recuerda a donde queria ir para volver despues del login. */
export const authGuard: CanActivateFn = (_ruta, estado) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  if (sesion.autenticado()) return true;
  return router.createUrlTree(['/login'], { queryParams: { volverA: estado.url } });
};

/**
 * Exige alguno de los roles declarados en `data.roles` de la ruta.
 * Uso: { path: 'usuarios', canActivate: [authGuard, rolGuard], data: { roles: ['administrador'] } }
 */
export const rolGuard: CanActivateFn = (ruta) => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  const avisos = inject(Notificaciones);
  const requeridos = (ruta.data['roles'] ?? []) as string[];

  if (requeridos.length === 0 || sesion.tieneAlgunRol(...requeridos)) return true;

  avisos.error(
    `Esta seccion es solo para: ${requeridos.join(', ')}. Tu rol es: ${sesion.roles().join(', ') || 'ninguno'}.`,
  );
  return router.createUrlTree([rutaInicial(sesion.roles())]);
};

/** Impide volver al login con la sesion ya iniciada. */
export const invitadoGuard: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  if (!sesion.autenticado()) return true;
  return router.createUrlTree([rutaInicial(sesion.roles())]);
};
