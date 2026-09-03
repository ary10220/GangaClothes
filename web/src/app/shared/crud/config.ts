import { FiltroEstado } from '../estado/estado';

export type { FiltroEstado };

export type TipoCampo = 'texto' | 'parrafo' | 'numero' | 'fecha' | 'color' | 'select';

export interface CampoCrud {
  /** Clave tal cual la espera la API. */
  nombre: string;
  etiqueta: string;
  tipo: TipoCampo;
  requerido?: boolean;
  /** Por defecto todos los campos se muestran en la tabla. */
  enTabla?: boolean;
  marcador?: string;
  /** Solo para tipo 'select': de donde salen las opciones. */
  origen?: OrigenOpciones;
  /** Ocupa las dos columnas del formulario. */
  ancho?: 'completo';
}

export interface OrigenOpciones {
  /** Ruta relativa a API_URL, p. ej. 'admin/temporadas'. */
  ruta: string;
  /** Campo de la respuesta que se muestra al usuario. Por defecto 'nombre'. */
  etiqueta?: string;
}

export interface ConfigCrud {
  /** Titulo de la pantalla, p. ej. 'Categorias'. */
  titulo: string;
  /** En singular y minuscula, para los mensajes: 'la categoria'. */
  singular: string;
  /** Ruta relativa a API_URL, p. ej. 'admin/categorias'. */
  ruta: string;
  campos: CampoCrud[];
  /** Texto bajo el titulo (caso de uso al que corresponde). */
  nota?: string;
  /**
   * True cuando la tabla tiene columna `activo`: el backend desactiva en vez
   * de borrar si hay registros asociados, asi que la pantalla ofrece el filtro
   * Activos / Inactivos / Todos y el boton Reactivar. En los demas recursos
   * eliminar es eliminar y el selector no se muestra.
   */
  archivable?: boolean;
}


export interface Opcion {
  id: number;
  etiqueta: string;
}
