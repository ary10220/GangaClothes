import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { API_URL } from '../../core/api';
import { fechaCortaLocal } from '../../shared/formato';

/** Un grupo de ventas ya sumado (backend: reportes/service.py `_cerrar`). */
export interface GrupoVentas {
  clave: string | number;
  etiqueta: string;
  ventas: number;
  unidades: number;
  subtotal: number;
  descuento: number;
  total: number;
  ganancia: number;
  ticket_promedio: number;
  margen_porcentaje: number;
  participacion?: number;
}

export interface TotalesVentas {
  ventas: number;
  unidades: number;
  subtotal: number;
  descuento: number;
  total: number;
  costo: number;
  ganancia: number;
  ticket_promedio: number;
  margen_porcentaje: number;
  ganancia_por_unidad: number;
}

export interface GrupoLineas {
  clave: number;
  etiqueta: string;
  unidades: number;
  total: number;
  ganancia: number;
  participacion: number;
}

/** GET /api/reportes/dashboard */
export interface DashboardDatos {
  periodo: { desde: string; hasta: string; dias: number; hoy: string };
  indicadores: TotalesVentas & {
    total_periodo_anterior: number;
    variacion_porcentaje: number | null;
    ganancia_promedio_por_prenda: number;
    margen_promedio_porcentaje: number;
    prendas_activas: number;
    reservas_activas: number;
    alertas_stock: number;
    unidades_en_stock: number;
    valor_inventario_costo: number;
    valor_inventario_venta: number;
    compras_pendientes: number;
    promociones_vigentes: number;
  };
  ventas_por_dia: { fecha: string; ventas: number; total: number; ganancia: number }[];
  por_canal: GrupoVentas[];
  por_sucursal: GrupoVentas[];
  por_categoria: GrupoLineas[];
  top_prendas: GrupoLineas[];
  metodos_pago: { metodo: string; pagos: number; total: number }[];
  reservas_por_estado: { estado: string; reservas: number }[];
}

/** GET /api/reportes/ventas */
export interface ReporteVentas {
  periodo: { desde: string; hasta: string };
  totales: TotalesVentas;
  por_periodo: GrupoVentas[];
  por_sucursal: GrupoVentas[];
  por_canal: GrupoVentas[];
  por_sucursal_y_canal: GrupoVentas[];
  ventas: {
    id: number;
    fecha: string;
    nro_comprobante: string | null;
    sucursal: string;
    canal: string;
    unidades: number;
    subtotal: number;
    descuento: number;
    total: number;
    ganancia: number;
  }[];
}

export interface FilaStock {
  prenda_id?: number;
  prenda?: string;
  sucursal_id: number;
  sucursal: string;
  variantes: number;
  unidades: number;
  reservadas: number;
  disponibles: number;
  bajo_minimo: number;
  sin_stock: number;
  valor_costo: number;
  valor_venta: number;
}

/** GET /api/reportes/inventario */
export interface ReporteInventario {
  periodo: { desde: string; hasta: string };
  totales: Omit<FilaStock, 'sucursal_id' | 'sucursal' | 'variantes'>;
  por_sucursal: FilaStock[];
  stock: FilaStock[];
  movimientos_por_tipo: { tipo: string; movimientos: number; unidades: number }[];
  movimientos: {
    id: number;
    fecha: string | null;
    tipo: string;
    sku: string;
    prenda: string;
    talla: string;
    color: string;
    sucursal: string;
    cantidad: number;
    motivo: string | null;
    usuario: string | null;
  }[];
}

export interface FilaMargen {
  prenda_id: number;
  prenda: string;
  categoria: string | null;
  publicado: boolean;
  precio_venta: number;
  costo: number;
  ganancia_unitaria: number;
  margen_porcentaje: number;
  promocion: string | null;
  precio_con_promocion: number;
  ganancia_con_promocion: number;
  unidades_vendidas: number;
  ingreso: number;
  descuento_otorgado: number;
  ganancia_realizada: number;
}

/** GET /api/reportes/margen */
export interface ReporteMargen {
  periodo: { desde: string; hasta: string };
  resumen: {
    prendas: number;
    ganancia_promedio_por_prenda: number;
    margen_promedio_porcentaje: number;
    ganancia_promedio_por_unidad_vendida: number;
    unidades_vendidas: number;
    ganancia_realizada: number;
    mayor_ganancia: string | null;
    menor_ganancia: string | null;
  };
  prendas: FilaMargen[];
}

export interface FiltrosReporte {
  desde?: string | null;
  hasta?: string | null;
  sucursal_id?: number | null;
  canal?: string | null;
  agrupar?: string | null;
}

export type NombreReporte = 'ventas' | 'inventario' | 'margen';

/** Colores de serie de los graficos (validados para daltonismo; siempre van con su etiqueta escrita). */
export const COLOR_CANAL: Record<string, string> = { caja: '#e8175d', web: '#2a78d6', movil: '#c98500' };
export const ETIQUETA_CANAL: Record<string, string> = { caja: 'Caja', web: 'Web', movil: 'App movil' };

@Injectable({ providedIn: 'root' })
export class ReportesService {
  private http = inject(HttpClient);

  private parametros(filtros: FiltrosReporte): HttpParams {
    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== null && valor !== undefined && valor !== '') params = params.set(clave, String(valor));
    }
    return params;
  }

  dashboard(filtros: FiltrosReporte): Observable<DashboardDatos> {
    return this.http.get<DashboardDatos>(`${API_URL}/reportes/dashboard`, { params: this.parametros(filtros) });
  }

  ventas(filtros: FiltrosReporte): Observable<ReporteVentas> {
    return this.http.get<ReporteVentas>(`${API_URL}/reportes/ventas`, { params: this.parametros(filtros) });
  }

  inventario(filtros: FiltrosReporte): Observable<ReporteInventario> {
    return this.http.get<ReporteInventario>(`${API_URL}/reportes/inventario`, { params: this.parametros(filtros) });
  }

  margen(filtros: FiltrosReporte): Observable<ReporteMargen> {
    return this.http.get<ReporteMargen>(`${API_URL}/reportes/margen`, { params: this.parametros(filtros) });
  }

  /**
   * Baja el reporte como CSV (lo arma el backend, listo para Excel). Va por
   * HttpClient y no por un enlace directo porque la ruta necesita el token.
   */
  descargarCsv(reporte: NombreReporte, filtros: FiltrosReporte): Observable<string> {
    const params = this.parametros(filtros).set('formato', 'csv');
    return this.http
      .get(`${API_URL}/reportes/${reporte}`, { params, responseType: 'blob', observe: 'response' })
      .pipe(
        map((respuesta) => {
          const cabecera = respuesta.headers.get('content-disposition') ?? '';
          const nombre = /filename="?([^";]+)"?/.exec(cabecera)?.[1] ?? `${reporte}.csv`;
          const url = URL.createObjectURL(respuesta.body as Blob);
          const enlace = document.createElement('a');
          enlace.href = url;
          enlace.download = nombre;
          enlace.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
          return nombre;
        }),
      );
  }
}

/** "2026-09-14" -> "14/09" (o "14/09/2026" con `conAnio`). Un instante con
 * hora se pasa antes a la zona local: la conversion vive en shared/formato. */
export const fechaCorta = fechaCortaLocal;

/** Fecha local de hoy (o de hace `dias`) como "AAAA-MM-DD", para los campos de fecha. */
export function isoLocal(diasAtras = 0): string {
  const d = new Date();
  d.setDate(d.getDate() - diasAtras);
  const dos = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
}
