export type Rol = 'administrador' | 'encargado' | 'cajero' | 'cliente';

export interface Usuario {
  id: number;
  nombre: string;
  apellido: string | null;
  email: string;
  roles: Rol[];
}

export interface SesionRespuesta {
  access_token: string;
  token_type: string;
  usuario: Usuario;
}
