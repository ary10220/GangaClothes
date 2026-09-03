import { ConfigCrud } from '../../../shared/crud/config';

/**
 * Una entrada por cada catalogo generado con la fabrica del backend.
 * Cambian los campos, no el comportamiento: la pantalla es siempre `Crud`.
 */

export const CATEGORIAS: ConfigCrud = {
  titulo: 'Categorias',
  singular: 'la categoria',
  ruta: 'admin/categorias',
  archivable: true,
  nota: 'CU4 · tipos de prenda',
  campos: [
    { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto', requerido: true, marcador: 'Poleras' },
    { nombre: 'descripcion', etiqueta: 'Descripcion', tipo: 'parrafo', ancho: 'completo' },
  ],
};

export const TALLAS: ConfigCrud = {
  titulo: 'Tallas',
  singular: 'la talla',
  ruta: 'admin/tallas',
  nota: 'CU5 · el orden define como se listan',
  campos: [
    { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto', requerido: true, marcador: 'M' },
    { nombre: 'orden', etiqueta: 'Orden', tipo: 'numero', marcador: '2' },
  ],
};

export const COLORES: ConfigCrud = {
  titulo: 'Colores',
  singular: 'el color',
  ruta: 'admin/colores',
  nota: 'CU5 · el hex se usa en el catalogo y el probador',
  campos: [
    { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto', requerido: true, marcador: 'Rojo' },
    { nombre: 'codigo_hex', etiqueta: 'Color', tipo: 'color' },
  ],
};

export const TEMPORADAS: ConfigCrud = {
  titulo: 'Temporadas',
  singular: 'la temporada',
  ruta: 'admin/temporadas',
  archivable: true,
  nota: 'CU6 · agrupan colecciones por periodo',
  campos: [
    { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto', requerido: true, marcador: 'Verano 2026' },
    { nombre: 'fecha_inicio', etiqueta: 'Inicio', tipo: 'fecha' },
    { nombre: 'fecha_fin', etiqueta: 'Fin', tipo: 'fecha' },
  ],
};

export const COLECCIONES: ConfigCrud = {
  titulo: 'Colecciones',
  singular: 'la coleccion',
  ruta: 'admin/colecciones',
  nota: 'CU6 · cada coleccion pertenece a una temporada',
  campos: [
    {
      nombre: 'temporada_id',
      etiqueta: 'Temporada',
      tipo: 'select',
      requerido: true,
      origen: { ruta: 'admin/temporadas' },
    },
    { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto', requerido: true, marcador: 'Primavera-Verano' },
    { nombre: 'anio', etiqueta: 'Anio', tipo: 'numero', marcador: '2026' },
    { nombre: 'descripcion', etiqueta: 'Descripcion', tipo: 'parrafo', ancho: 'completo' },
  ],
};

export const CIUDADES: ConfigCrud = {
  titulo: 'Ciudades',
  singular: 'la ciudad',
  ruta: 'admin/ciudades',
  nota: 'CU8 · donde hay sucursales',
  campos: [
    {
      nombre: 'nombre',
      etiqueta: 'Nombre',
      tipo: 'texto',
      requerido: true,
      marcador: 'Santa Cruz de la Sierra',
    },
    { nombre: 'departamento', etiqueta: 'Departamento', tipo: 'texto', marcador: 'Santa Cruz' },
  ],
};

export const SUCURSALES: ConfigCrud = {
  titulo: 'Sucursales',
  singular: 'la sucursal',
  ruta: 'admin/sucursales',
  archivable: true,
  nota: 'CU8 · cada sucursal maneja su propio inventario',
  campos: [
    { nombre: 'ciudad_id', etiqueta: 'Ciudad', tipo: 'select', requerido: true, origen: { ruta: 'admin/ciudades' } },
    { nombre: 'nombre', etiqueta: 'Nombre', tipo: 'texto', requerido: true, marcador: 'Sucursal Central' },
    { nombre: 'direccion', etiqueta: 'Direccion', tipo: 'texto', marcador: 'Av. Principal #123' },
    { nombre: 'telefono', etiqueta: 'Telefono', tipo: 'texto', marcador: '3-3456789' },
    { nombre: 'horario', etiqueta: 'Horario', tipo: 'texto', marcador: 'Lun-Sab 9:00-20:00', ancho: 'completo' },
  ],
};
