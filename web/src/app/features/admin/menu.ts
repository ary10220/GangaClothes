import { Rol } from '../../core/modelos';

export interface ItemMenu {
  etiqueta: string;
  ruta: string;
  roles: Rol[];
  /** Si se indica, el item solo aparece cuando la sesion tiene ese permiso. */
  permiso?: string;
  /** Los casos de uso de iteraciones posteriores se listan, pero aun sin pantalla. */
  disponible: boolean;
}

export interface GrupoMenu {
  titulo: string;
  items: ItemMenu[];
}

const ADMIN: Rol[] = ['administrador'];

export const MENU: GrupoMenu[] = [
  {
    titulo: 'General',
    items: [{ etiqueta: 'Panel', ruta: '/admin', roles: ['administrador', 'encargado', 'cajero'], disponible: true }],
  },
  {
    titulo: 'Analisis',
    items: [
      {
        etiqueta: 'Dashboard',
        ruta: '/admin/dashboard',
        roles: ['administrador', 'encargado'],
        permiso: 'reportes:ver',
        disponible: true,
      },
      {
        etiqueta: 'Reportes',
        ruta: '/admin/reportes',
        roles: ['administrador', 'encargado'],
        permiso: 'reportes:ver',
        disponible: true,
      },
    ],
  },
  {
    titulo: 'Seguridad',
    items: [
      { etiqueta: 'Usuarios', ruta: '/admin/usuarios', roles: ADMIN, disponible: true },
      { etiqueta: 'Roles y permisos', ruta: '/admin/roles', roles: ADMIN, disponible: true },
      { etiqueta: 'Bitacora', ruta: '/admin/bitacora', roles: ADMIN, disponible: true },
    ],
  },
  {
    titulo: 'Catalogos base',
    items: [
      { etiqueta: 'Categorias', ruta: '/admin/categorias', roles: ADMIN, disponible: true },
      { etiqueta: 'Tallas', ruta: '/admin/tallas', roles: ADMIN, disponible: true },
      { etiqueta: 'Colores', ruta: '/admin/colores', roles: ADMIN, disponible: true },
      { etiqueta: 'Temporadas', ruta: '/admin/temporadas', roles: ADMIN, disponible: true },
      { etiqueta: 'Colecciones', ruta: '/admin/colecciones', roles: ADMIN, disponible: true },
    ],
  },
  {
    titulo: 'Red de tiendas',
    items: [
      { etiqueta: 'Ciudades', ruta: '/admin/ciudades', roles: ADMIN, disponible: true },
      { etiqueta: 'Sucursales', ruta: '/admin/sucursales', roles: ADMIN, disponible: true },
    ],
  },
  {
    titulo: 'Productos',
    items: [
      { etiqueta: 'Prendas y variantes', ruta: '/admin/prendas', roles: ADMIN, disponible: true },
      { etiqueta: 'Promociones', ruta: '/admin/promociones', roles: ADMIN, permiso: 'promociones:ver', disponible: true },
    ],
  },
  {
    titulo: 'Operacion',
    items: [
      { etiqueta: 'Inventario', ruta: '/admin/inventario', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'Movimientos', ruta: '/admin/movimientos', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'Compras', ruta: '/admin/compras', roles: ['administrador', 'encargado'], disponible: true },
      { etiqueta: 'Proveedores', ruta: '/admin/proveedores', roles: ['administrador', 'encargado'], disponible: true },
      {
        etiqueta: 'Oferta de proveedores',
        ruta: '/admin/oferta-proveedores',
        roles: ['administrador', 'encargado'],
        permiso: 'inventario:crear',
        disponible: true,
      },
      { etiqueta: 'Reservas', ruta: '/admin/reservas', roles: ['administrador', 'encargado'], disponible: true },
      {
        etiqueta: 'Envios a domicilio',
        ruta: '/admin/envios',
        roles: ['administrador', 'encargado', 'cajero'],
        permiso: 'envios:ver',
        disponible: true,
      },
      { etiqueta: 'Caja', ruta: '/admin/caja', roles: ['administrador', 'cajero'], disponible: true },
    ],
  },
  {
    titulo: 'Portal del proveedor',
    items: [{ etiqueta: 'Mi oferta', ruta: '/proveedor', roles: ['proveedor'], permiso: 'oferta:ver', disponible: true }],
  },
];

/** Deja solo los grupos e items que el rol (y, si el item lo pide, el permiso) del usuario puede ver. */
export function menuParaRoles(roles: string[], permisos: string[] = []): GrupoMenu[] {
  return MENU.map((grupo) => ({
    ...grupo,
    items: grupo.items.filter(
      (item) => item.roles.some((r) => roles.includes(r)) && (!item.permiso || permisos.includes(item.permiso)),
    ),
  })).filter((grupo) => grupo.items.length > 0);
}
