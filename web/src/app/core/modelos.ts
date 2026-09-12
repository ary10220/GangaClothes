export type Rol = 'administrador' | 'encargado' | 'cajero' | 'cliente';

export interface Usuario {
  id: number;
  nombre: string;
  apellido: string | null;
  email: string;
  /** Los roles son administrables, asi que no se limitan a los del sistema. */
  roles: string[];
  /** Permisos que le llegan por sus roles, en formato "modulo:accion". */
  permisos: string[];
}

export interface SesionRespuesta {
  access_token: string;
  token_type: string;
  usuario: Usuario;
}
