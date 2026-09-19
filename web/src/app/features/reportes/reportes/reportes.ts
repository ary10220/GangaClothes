import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { Observable } from 'rxjs';

import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SucursalActual } from '../../../core/sucursal-actual';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaLocal, moneda, porcentaje } from '../../../shared/formato';
import { BarrasH, FilaBarra } from '../../../shared/graficos/barras-h';
import { PuntoSerie, SerieDias } from '../../../shared/graficos/serie-dias';
import {
  COLOR_CANAL,
  ETIQUETA_CANAL,
  FiltrosReporte,
  NombreReporte,
  ReporteInventario,
  ReporteMargen,
  ReporteVentas,
  ReportesService,
  fechaCorta,
  isoLocal,
} from '../reportes.service';

type Agrupar = 'dia' | 'semana' | 'mes';

const REPORTES: OpcionFiltro<NombreReporte>[] = [
  { valor: 'ventas', etiqueta: 'Ventas' },
  { valor: 'inventario', etiqueta: 'Inventario y movimientos' },
  { valor: 'margen', etiqueta: 'Ganancia por prenda' },
];

const AGRUPACIONES: OpcionFiltro<Agrupar>[] = [
  { valor: 'dia', etiqueta: 'Por dia' },
  { valor: 'semana', etiqueta: 'Por semana' },
  { valor: 'mes', etiqueta: 'Por mes' },
];

const MOVIMIENTOS_VISIBLES = 60;

/**
 * CU19 Reportes: ventas por sucursal, canal y periodo; inventario valorizado
 * con sus movimientos; y ganancia por prenda. Los tres se exportan a CSV (lo
 * arma el backend) y se imprimen o guardan como PDF desde el navegador.
 */
@Component({
  selector: 'app-reportes',
  imports: [SelectorEstado, BarrasH, SerieDias],
  templateUrl: './reportes.html',
  styleUrl: './reportes.css',
})
export class Reportes {
  private servicio = inject(ReportesService);
  private avisos = inject(Notificaciones);
  readonly sucursales = inject(SucursalActual);

  /** `?reporte=margen` abre esa pestana (enlace desde el dashboard). */
  readonly reporteInicial = input<string>(undefined, { alias: 'reporte' });

  readonly opcionesReporte = REPORTES;
  readonly agrupaciones = AGRUPACIONES;
  readonly moneda = moneda;
  readonly pct = porcentaje;
  readonly canales = Object.entries(ETIQUETA_CANAL).map(([valor, etiqueta]) => ({ valor, etiqueta }));

  // ---- filtros ----
  readonly reporte = signal<NombreReporte>('ventas');
  readonly desde = signal(isoLocal(29));
  readonly hasta = signal(isoLocal());
  readonly sucursalId = signal<number | null>(null);
  readonly canal = signal<string | null>(null);
  readonly agrupar = signal<Agrupar>('dia');

  // ---- datos ----
  readonly ventas = signal<ReporteVentas | null>(null);
  readonly inventario = signal<ReporteInventario | null>(null);
  readonly margen = signal<ReporteMargen | null>(null);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);
  readonly exportando = signal(false);
  readonly todosLosMovimientos = signal(false);
  private pedido = 0;

  readonly errorFechas = computed(() =>
    !this.desde() || !this.hasta()
      ? 'Elegi las dos fechas del periodo.'
      : this.desde() > this.hasta()
        ? 'La fecha «desde» no puede ser posterior a «hasta».'
        : null,
  );

  readonly filtros = computed<FiltrosReporte>(() => ({
    desde: this.desde(),
    hasta: this.hasta(),
    sucursal_id: this.sucursalId(),
    canal: this.reporte() === 'ventas' ? this.canal() : null,
    agrupar: this.reporte() === 'ventas' ? this.agrupar() : null,
  }));

  readonly titulo = computed(() => REPORTES.find((r) => r.valor === this.reporte())?.etiqueta ?? '');
  readonly nombreSucursal = computed(
    () => this.sucursales.sucursales().find((s) => s.id === this.sucursalId())?.nombre ?? 'Todas las sucursales',
  );

  // ------------------------------------------------------------- graficos
  readonly serieVentas = computed<PuntoSerie[]>(() =>
    (this.ventas()?.por_periodo ?? []).map((g) => ({
      clave: String(g.clave),
      etiqueta: this.agrupar() === 'dia' ? fechaCorta(String(g.clave)) : g.etiqueta.replace('Semana del ', 'sem. '),
      valor: g.total,
      detalle: `${g.ventas} ${g.ventas === 1 ? 'venta' : 'ventas'} · ganancia Bs ${moneda(g.ganancia)}`,
    })),
  );

  readonly barrasSucursal = computed<FilaBarra[]>(() =>
    (this.ventas()?.por_sucursal ?? []).map((g) => ({
      etiqueta: g.etiqueta,
      valor: g.total,
      texto: `Bs ${moneda(g.total)}`,
      detalle: `${porcentaje(g.participacion ?? 0)} del total`,
    })),
  );

  readonly barrasCanal = computed<FilaBarra[]>(() =>
    (this.ventas()?.por_canal ?? []).map((g) => ({
      etiqueta: ETIQUETA_CANAL[g.etiqueta] ?? g.etiqueta,
      valor: g.total,
      texto: `Bs ${moneda(g.total)}`,
      detalle: `${porcentaje(g.participacion ?? 0)} del total`,
      color: COLOR_CANAL[g.etiqueta],
    })),
  );

  readonly barrasValorStock = computed<FilaBarra[]>(() =>
    (this.inventario()?.por_sucursal ?? []).map((s) => ({
      etiqueta: s.sucursal,
      valor: s.valor_costo,
      texto: `Bs ${moneda(s.valor_costo)}`,
      detalle: `${s.unidades} unidades · ${s.bajo_minimo} variantes en su minimo`,
    })),
  );

  readonly movimientosVisibles = computed(() => {
    const lista = this.inventario()?.movimientos ?? [];
    return this.todosLosMovimientos() ? lista : lista.slice(0, MOVIMIENTOS_VISIBLES);
  });

  readonly margenOrdenado = computed(() =>
    [...(this.margen()?.prendas ?? [])].sort((a, b) => b.ganancia_unitaria - a.ganancia_unitaria),
  );
  readonly mayorGanancia = computed(() => Math.max(1, ...this.margenOrdenado().map((p) => p.ganancia_unitaria)));

  constructor() {
    this.sucursales.cargar();
    effect(() => {
      const inicial = this.reporteInicial();
      if (inicial && REPORTES.some((r) => r.valor === inicial)) {
        untracked(() => this.reporte.set(inicial as NombreReporte));
      }
    });
    effect(() => {
      const reporte = this.reporte();
      const filtros = this.filtros();
      const invalido = this.errorFechas();
      untracked(() => {
        if (!invalido) this.cargar(reporte, filtros);
      });
    });
  }

  recargar(): void {
    if (!this.errorFechas()) this.cargar(this.reporte(), this.filtros());
  }

  private cargar(reporte: NombreReporte, filtros: FiltrosReporte): void {
    const pedido = ++this.pedido;
    this.cargando.set(true);
    this.error.set(null);
    const fuentes: Record<NombreReporte, () => Observable<unknown>> = {
      ventas: () => this.servicio.ventas(filtros),
      inventario: () => this.servicio.inventario(filtros),
      margen: () => this.servicio.margen(filtros),
    };
    fuentes[reporte]().subscribe({
      next: (datos) => {
        if (pedido !== this.pedido) return;
        if (reporte === 'ventas') this.ventas.set(datos as ReporteVentas);
        if (reporte === 'inventario') this.inventario.set(datos as ReporteInventario);
        if (reporte === 'margen') this.margen.set(datos as ReporteMargen);
        this.cargando.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.error.set(mensajeDeError(err, 'No se pudo generar el reporte.'));
        this.cargando.set(false);
      },
    });
  }

  // ---------------------------------------------------------------- filtros
  elegirSucursal(valor: string): void {
    this.sucursalId.set(valor ? Number(valor) : null);
  }

  elegirCanal(valor: string): void {
    this.canal.set(valor || null);
  }

  ultimosDias(dias: number): void {
    this.desde.set(isoLocal(dias - 1));
    this.hasta.set(isoLocal());
  }

  exportar(): void {
    this.exportando.set(true);
    this.servicio.descargarCsv(this.reporte(), this.filtros()).subscribe({
      next: (nombre) => {
        this.exportando.set(false);
        this.avisos.ok(`Se descargo ${nombre}: se abre directo en Excel.`);
      },
      error: (err) => {
        this.exportando.set(false);
        this.avisos.error(mensajeDeError(err, 'No se pudo exportar el reporte.'));
      },
    });
  }

  imprimir(): void {
    window.print();
  }

  // ----------------------------------------------------------- presentacion
  fecha(iso: string | null): string {
    return iso ? fechaCorta(iso, true) : '—';
  }

  /** Instante de la API (UTC) en la hora de quien mira la pantalla. */
  readonly fechaHora = fechaLocal;

  canalLegible(canal: string): string {
    return ETIQUETA_CANAL[canal] ?? canal;
  }

  ancho(valor: number): number {
    return Math.max(0, (valor / this.mayorGanancia()) * 100);
  }

  claseMovimiento(tipo: string): string {
    return tipo === 'ingreso' || tipo === 'devolucion' ? 'ok' : tipo === 'salida' ? 'rosa' : 'bajo';
  }
}
