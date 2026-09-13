import { Routes } from '@angular/router';

import { authGuard, invitadoGuard, rolGuard } from './core/auth.guard';
import {
  CATEGORIAS,
  CIUDADES,
  COLECCIONES,
  COLORES,
  PROVEEDORES,
  SUCURSALES,
  TALLAS,
  TEMPORADAS,
} from './features/admin/catalogos/configs';
import { ConfigCrud } from './shared/crud/config';

const SOLO_ADMIN = { roles: ['administrador'] };
/** Reservas y carrito son de la cuenta del cliente: el personal usa el panel. */
const SOLO_CLIENTE = { roles: ['cliente'] };
/** Panel del encargado de sucursal: inventario, movimientos, compras y reservas. */
const OPERACION_SUCURSAL = { roles: ['administrador', 'encargado'] };

/**
 * Los 7 catalogos comparten el componente `Crud`: lo unico que cambia es el
 * `config`, que llega como input gracias a `withComponentInputBinding()`.
 */
function rutaCrud(camino: string, config: ConfigCrud, acceso: { roles: string[] } = SOLO_ADMIN) {
  return {
    path: camino,
    canActivate: [rolGuard],
    data: { ...acceso, config },
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
    path: 'registro',
    canActivate: [invitadoGuard],
    loadComponent: () => import('./features/auth/registro/registro').then((m) => m.Registro),
  },
  {
    path: 'recuperar',
    canActivate: [invitadoGuard],
    loadComponent: () => import('./features/auth/recuperar/recuperar').then((m) => m.Recuperar),
  },
  {
    path: 'catalogo',
    loadComponent: () => import('./features/catalogo/catalogo').then((m) => m.Catalogo),
  },
  {
    path: 'mis-reservas',
    canActivate: [authGuard, rolGuard],
    data: SOLO_CLIENTE,
    loadComponent: () => import('./features/tienda/mis-reservas/mis-reservas').then((m) => m.MisReservas),
  },
  {
    path: 'carrito',
    canActivate: [authGuard, rolGuard],
    data: SOLO_CLIENTE,
    loadComponent: () => import('./features/tienda/carrito/carrito').then((m) => m.Carrito),
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
      {
        path: 'roles',
        canActivate: [rolGuard],
        data: SOLO_ADMIN,
        loadComponent: () => import('./features/admin/roles/roles').then((m) => m.Roles),
      },
      {
        path: 'bitacora',
        canActivate: [rolGuard],
        data: SOLO_ADMIN,
        loadComponent: () => import('./features/admin/bitacora/bitacora').then((m) => m.Bitacora),
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
      {
        path: 'inventario',
        canActivate: [rolGuard],
        data: OPERACION_SUCURSAL,
        loadComponent: () => import('./features/inventario/inventario/inventario').then((m) => m.Inventario),
      },
      {
        path: 'movimientos',
        canActivate: [rolGuard],
        data: OPERACION_SUCURSAL,
        loadComponent: () => import('./features/inventario/movimientos/movimientos').then((m) => m.Movimientos),
      },
      {
        path: 'compras',
        canActivate: [rolGuard],
        data: OPERACION_SUCURSAL,
        loadComponent: () => import('./features/inventario/compras/compras').then((m) => m.Compras),
      },
      rutaCrud('proveedores', PROVEEDORES, OPERACION_SUCURSAL),
      {
        path: 'reservas',
        canActivate: [rolGuard],
        data: OPERACION_SUCURSAL,
        loadComponent: () =>
          import('./features/reservas/sucursal/reservas-sucursal').then((m) => m.ReservasSucursal),
      },
      {
        path: 'caja',
        canActivate: [rolGuard],
        data: { roles: ['administrador', 'cajero'] },
        loadComponent: () => import('./features/caja/caja').then((m) => m.Caja),
      },
    ],
  },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
