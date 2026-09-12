import { Rol } from '../../core/modelos';

export interface ItemMenu {
  etiqueta: string;
  ruta: string;
  roles: Rol[];
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
    titulo: 'Seguridad',
    items: [{ etiqueta: 'Usuarios y roles', ruta: '/admin/usuarios', roles: ADMIN, disponible: true }],
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
    items: [{ etiqueta: 'Prendas y variantes', ruta: '/admin/prendas', roles: ADMIN, disponible: true }],
  },
  {
    titulo: 'Operacion',
    items: [
      { etiqueta: 'Inventario', ruta: '/admin/inventario', roles: ['administrador', 'encargado'], disponible: false },
      { etiqueta: 'Caja', ruta: '/caja', roles: ['administrador', 'cajero'], disponible: false },
    ],
  },
];

/** Deja solo los grupos e items que el rol del usuario puede ver. */
export function menuParaRoles(roles: Rol[]): GrupoMenu[] {
  return MENU.map((grupo) => ({
    ...grupo,
    items: grupo.items.filter((item) => item.roles.some((r) => roles.includes(r))),
  })).filter((grupo) => grupo.items.length > 0);
}
