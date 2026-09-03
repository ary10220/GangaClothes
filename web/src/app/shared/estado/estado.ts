/**
 * Filtro Activos / Inactivos / Todos, compartido por el CRUD generico y la
 * pantalla de prendas. Vive aparte porque ambas lo usan igual.
 */
export type FiltroEstado = 'activos' | 'inactivos' | 'todos';

/** Una fila cualquiera de la API. Solo las tablas archivables traen `activo`. */
type Fila = Record<string, unknown>;

export function esInactivo(fila: Fila): boolean {
  return 'activo' in fila && fila['activo'] === false;
}

export function filtrarPorEstado<T extends Fila>(filas: T[], estado: FiltroEstado): T[] {
  if (estado === 'activos') return filas.filter((f) => !esInactivo(f));
  if (estado === 'inactivos') return filas.filter((f) => esInactivo(f));
  return filas;
}

function sustantivo(cantidad: number, estado: FiltroEstado, archivable: boolean): string {
  if (!archivable || estado === 'todos') return cantidad === 1 ? 'registro' : 'registros';
  if (estado === 'activos') return cantidad === 1 ? 'activo' : 'activos';
  return cantidad === 1 ? 'inactivo' : 'inactivos';
}

/** "3 activos", "1 inactivo", "4 registros"; con busqueda activa, "2 de 5 activos". */
export function textoPie(
  mostrados: number,
  total: number,
  estado: FiltroEstado,
  archivable: boolean,
): string {
  const nombre = sustantivo(total, estado, archivable);
  return mostrados === total ? `${total} ${nombre}` : `${mostrados} de ${total} ${nombre}`;
}

/** Texto del estado vacio: distingue "no hay nada" de "esta todo archivado". */
export function textoVacio(
  totalFilas: number,
  archivados: number,
  estado: FiltroEstado,
  titulo: string,
): string {
  if (totalFilas === 0) return `Todavia no hay registros en ${titulo.toLowerCase()}.`;
  if (estado === 'inactivos') return 'No hay registros archivados.';
  if (archivados === 1) return 'No hay registros activos. Hay 1 archivado: miralo en «Inactivos».';
  if (archivados > 1) {
    return `No hay registros activos. Hay ${archivados} archivados: miralos en «Inactivos».`;
  }
  return `Todavia no hay registros en ${titulo.toLowerCase()}.`;
}
