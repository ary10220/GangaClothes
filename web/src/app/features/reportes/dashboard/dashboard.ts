import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SucursalActual } from '../../../core/sucursal-actual';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { moneda, porcentaje } from '../../../shared/formato';
import { BarrasH, FilaBarra } from '../../../shared/graficos/barras-h';
import { PuntoSerie, SerieDias } from '../../../shared/graficos/serie-dias';
import {
  COLOR_CANAL,
  DashboardDatos,
  ETIQUETA_CANAL,
  ReporteMargen,
  ReportesService,
  fechaCorta,
  isoLocal,
} from '../reportes.service';

type Periodo = '7' | '30' | '90';

const PERIODOS: OpcionFiltro<Periodo>[] = [
  { valor: '7', etiqueta: '7 dias' },
  { valor: '30', etiqueta: '30 dias' },
  { valor: '90', etiqueta: '90 dias' },
];

/**
 * CU19 Dashboard: los indicadores principales de la tienda, con la ganancia
 * promedio por prenda (precio_venta - costo) que pide el enunciado. Solo
 * cuentan ventas pagadas. Todo sale de /api/reportes: aca no se calcula nada.
 */
@Component({
  selector: 'app-dashboard',
  imports: [RouterLink, SelectorEstado, BarrasH, SerieDias],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class Dashboard {
  private reportes = inject(ReportesService);
  private avisos = inject(Notificaciones);
  readonly sucursales = inject(SucursalActual);

  readonly periodos = PERIODOS;
  readonly moneda = moneda;
  readonly pct = porcentaje;

  readonly periodo = signal<Periodo>('30');
  /** null = todas las sucursales. */
  readonly sucursalId = signal<number | null>(null);

  readonly datos = signal<DashboardDatos | null>(null);
  readonly margen = signal<ReporteMargen | null>(null);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly exportando = signal(false);
  private pedido = 0;

  readonly filtros = computed(() => ({
    desde: isoLocal(Number(this.periodo()) - 1),
    hasta: isoLocal(),
    sucursal_id: this.sucursalId(),
  }));

  readonly nombreSucursal = computed(
    () => this.sucursales.sucursales().find((s) => s.id === this.sucursalId())?.nombre ?? 'Todas las sucursales',
  );

  // ------------------------------------------------------------- graficos
  readonly serie = computed<PuntoSerie[]>(() =>
    (this.datos()?.ventas_por_dia ?? []).map((d) => ({
      clave: d.fecha,
      etiqueta: fechaCorta(d.fecha),
      valor: d.total,
      detalle:
        d.ventas === 0
          ? 'sin ventas'
          : `${d.ventas} ${d.ventas === 1 ? 'venta' : 'ventas'} · ganancia Bs ${moneda(d.ganancia)}`,
    })),
  );

  readonly porCanal = computed<FilaBarra[]>(() =>
    (this.datos()?.por_canal ?? []).map((c) => ({
      etiqueta: ETIQUETA_CANAL[c.etiqueta] ?? c.etiqueta,
      valor: c.total,
      texto: `Bs ${moneda(c.total)}`,
      detalle: `${porcentaje(c.participacion ?? 0)} · ${c.ventas} ${c.ventas === 1 ? 'venta' : 'ventas'} · ticket Bs ${moneda(c.ticket_promedio)}`,
      color: COLOR_CANAL[c.etiqueta],
    })),
  );

  readonly porSucursal = computed<FilaBarra[]>(() =>
    (this.datos()?.por_sucursal ?? []).map((s) => ({
      etiqueta: s.etiqueta,
      valor: s.total,
      texto: `Bs ${moneda(s.total)}`,
      detalle: `${porcentaje(s.participacion ?? 0)} · ${s.ventas} ventas · margen ${porcentaje(s.margen_porcentaje)}`,
    })),
  );

  readonly porCategoria = computed<FilaBarra[]>(() =>
    (this.datos()?.por_categoria ?? []).map((c) => ({
      etiqueta: c.etiqueta,
      valor: c.total,
      texto: `Bs ${moneda(c.total)}`,
      detalle: `${c.unidades} unidades · ganancia Bs ${moneda(c.ganancia)}`,
    })),
  );

  readonly topPrendas = computed<FilaBarra[]>(() =>
    (this.datos()?.top_prendas ?? []).map((p) => ({
      etiqueta: p.etiqueta,
      valor: p.total,
      texto: `Bs ${moneda(p.total)}`,
      detalle: `${p.unidades} unidades · ganancia Bs ${moneda(p.ganancia)}`,
    })),
  );

  /** Ganancia unitaria de cada prenda, de mayor a menor: de aca sale el promedio. */
  readonly gananciaPorPrenda = computed(() =>
    [...(this.margen()?.prendas ?? [])].sort((a, b) => b.ganancia_unitaria - a.ganancia_unitaria),
  );
  readonly mayorGanancia = computed(() => Math.max(1, ...this.gananciaPorPrenda().map((p) => p.ganancia_unitaria)));

  constructor() {
    this.sucursales.cargar();
    effect(() => {
      const filtros = this.filtros();
      untracked(() => this.cargar(filtros));
    });
  }

  recargar(): void {
    this.cargar(this.filtros());
  }

  private cargar(filtros: { desde: string; hasta: string; sucursal_id: number | null }): void {
    const pedido = ++this.pedido;
    this.cargando.set(true);
    this.error.set(null);
    forkJoin({
      datos: this.reportes.dashboard(filtros),
      margen: this.reportes.margen(filtros),
    }).subscribe({
      next: ({ datos, margen }) => {
        if (pedido !== this.pedido) return;
        this.datos.set(datos);
        this.margen.set(margen);
        this.cargando.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.error.set(mensajeDeError(err, 'No se pudo cargar el dashboard.'));
        this.cargando.set(false);
      },
    });
  }

  elegirSucursal(valor: string): void {
    this.sucursalId.set(valor ? Number(valor) : null);
  }

  exportar(): void {
    this.exportando.set(true);
    this.reportes.descargarCsv('ventas', this.filtros()).subscribe({
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
  fecha(iso: string): string {
    return fechaCorta(iso, true);
  }

  ancho(valor: number): number {
    return Math.max(0, (valor / this.mayorGanancia()) * 100);
  }

  textoVariacion(v: number | null): string {
    if (v === null) return 'sin ventas en el periodo anterior';
    return `${v > 0 ? '▲' : v < 0 ? '▼' : '='} ${Math.abs(v).toLocaleString('es-BO', { maximumFractionDigits: 1 })}% vs. periodo anterior`;
  }
}
