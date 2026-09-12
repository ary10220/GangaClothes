import { Routes } from '@angular/router';

import { authGuard, invitadoGuard, rolGuard } from './core/auth.guard';
import {
  CATEGORIAS,
  CIUDADES,
  COLECCIONES,
  COLORES,
  SUCURSALES,
  TALLAS,
  TEMPORADAS,
} from './features/admin/catalogos/configs';
import { ConfigCrud } from './shared/crud/config';

const SOLO_ADMIN = { roles: ['administrador'] };

/**
 * Los 7 catalogos comparten el componente `Crud`: lo unico que cambia es el
 * `config`, que llega como input gracias a `withComponentInputBinding()`.
 */
function rutaCrud(camino: string, config: ConfigCrud) {
  return {
    path: camino,
    canActivate: [rolGuard],
    data: { ...SOLO_ADMIN, config },
    loadComponent: () => import('./shared/crud/crud').then((m) => m.Crud),
  };
}

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [invitadoGuard],
    loadComponent: () => import('./features/auth/login/login').then((m) => m.Login),
  },
  {
    path: 'catalogo',
    loadComponent: () => import('./features/catalogo/catalogo').then((m) => m.Catalogo),
  },
  {
    path: 'admin',
    canActivate: [authGuard, rolGuard],
    data: { roles: ['administrador', 'encargado', 'cajero'] },
    loadComponent: () => import('./features/admin/shell').then((m) => m.AdminShell),
    children: [
      {
        path: '',
        loadComponent: () => import('./features/admin/inicio/inicio').then((m) => m.AdminInicio),
      },
      {
        path: 'usuarios',
        canActivate: [rolGuard],
        data: SOLO_ADMIN,
        loadComponent: () => import('./features/admin/usuarios/usuarios').then((m) => m.Usuarios),
      },
      rutaCrud('categorias', CATEGORIAS),
      rutaCrud('tallas', TALLAS),
      rutaCrud('colores', COLORES),
      rutaCrud('temporadas', TEMPORADAS),
      rutaCrud('colecciones', COLECCIONES),
      rutaCrud('ciudades', CIUDADES),
      rutaCrud('sucursales', SUCURSALES),
      {
        path: 'prendas',
        canActivate: [rolGuard],
        data: SOLO_ADMIN,
        loadComponent: () => import('./features/admin/prendas/prendas').then((m) => m.Prendas),
      },
    ],
  },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
