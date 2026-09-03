/**
 * Atajos de login para la demostracion en clase (usuarios de backend/seed.py).
 * En la compilacion de produccion este archivo se reemplaza por
 * `cuentas-demo.prod.ts`, que devuelve una lista vacia: asi las credenciales
 * no viajan dentro del bundle publicado en Vercel.
 */
export interface CuentaDemo {
  rol: string;
  email: string;
  password: string;
}

export const CUENTAS_DEMO: CuentaDemo[] = [
  { rol: 'administrador', email: 'admin@gangaclothes.com', password: 'Admin123' },
  { rol: 'encargado', email: 'encargado@gangaclothes.com', password: 'Encargado123' },
  { rol: 'cajero', email: 'cajero@gangaclothes.com', password: 'Cajero123' },
];
