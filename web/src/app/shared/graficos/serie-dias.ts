import { Component, computed, input, signal } from '@angular/core';

import { moneda } from '../formato';

export interface PuntoSerie {
  /** Clave del periodo, por ejemplo "2026-09-14". */
  clave: string;
  /** Como se muestra en el eje y en el tooltip: "14/09". */
  etiqueta: string;
  valor: number;
  /** Segunda linea del tooltip: "3 ventas · ganancia Bs 410,00". */
  detalle?: string;
}

const ANCHO = 760;
const ALTO = 230;
const MARGEN = { arriba: 14, derecha: 8, abajo: 26, izquierda: 52 };

/** Redondea hacia arriba a un numero "lindo" para el tope del eje: 1, 2, 2.5, 5 o 10 x 10^n. */
function topeLindo(maximo: number): number {
  if (maximo <= 0) return 1;
  const potencia = Math.pow(10, Math.floor(Math.log10(maximo)));
  const fraccion = maximo / potencia;
  const paso = fraccion <= 1 ? 1 : fraccion <= 2 ? 2 : fraccion <= 2.5 ? 2.5 : fraccion <= 5 ? 5 : 10;
  return paso * potencia;
}

/**
 * Columnas de una sola serie a lo largo del tiempo (ventas por dia, semana o
 * mes), en SVG y sin librerias. Un solo eje, grilla discreta, los periodos sin
 * ventas se dibujan en cero y cada columna tiene su tooltip al pasar el mouse
 * o al enfocarla con el teclado.
 */
@Component({
  selector: 'app-serie-dias',
  template: `
    <div class="lienzo">
      <svg [attr.viewBox]="'0 0 ' + ancho + ' ' + alto" role="img" [attr.aria-label]="titulo()">
        @for (marca of marcas(); track marca.valor) {
          <line class="grilla" [attr.x1]="margen.izquierda" [attr.x2]="ancho - margen.derecha" [attr.y1]="marca.y" [attr.y2]="marca.y" />
          <text class="eje" [attr.x]="margen.izquierda - 8" [attr.y]="marca.y + 3.5" text-anchor="end">{{ marca.texto }}</text>
        }
        @for (c of columnas(); track c.clave; let i = $index) {
          <g
            class="columna"
            tabindex="0"
            [class.activa]="activa() === i"
            [attr.aria-label]="c.etiqueta + ': Bs ' + moneda(c.valor)"
            (mouseenter)="activa.set(i)"
            (mouseleave)="activa.set(null)"
            (focus)="activa.set(i)"
            (blur)="activa.set(null)"
          >
            <!-- zona sensible mas grande que la marca -->
            <rect class="zona" [attr.x]="c.x0" [attr.y]="margen.arriba" [attr.width]="c.paso" [attr.height]="altoUtil" />
            @if (c.valor > 0) {
              <path class="marca" [attr.d]="c.forma" />
            } @else {
              <rect class="cero" [attr.x]="c.x" [attr.y]="base - 1.5" [attr.width]="c.w" height="1.5" />
            }
          </g>
          @if (c.rotulo) {
            <text class="eje" [attr.x]="c.x + c.w / 2" [attr.y]="alto - 8" text-anchor="middle">{{ c.etiqueta }}</text>
          }
        }
        <line class="base" [attr.x1]="margen.izquierda" [attr.x2]="ancho - margen.derecha" [attr.y1]="base" [attr.y2]="base" />
      </svg>

      @if (tooltip(); as t) {
        <div class="tooltip" [style.left.%]="t.izquierda" [class.a-la-izquierda]="t.izquierda > 70">
          <span class="ceja">{{ t.etiqueta }}</span>
          <b class="mono">Bs {{ moneda(t.valor) }}</b>
          @if (t.detalle) {
            <span class="detalle">{{ t.detalle }}</span>
          }
        </div>
      }
    </div>
  `,
  styles: `
    .lienzo {
      position: relative;
    }
    svg {
      display: block;
      width: 100%;
      height: auto;
      overflow: visible;
    }
    .grilla {
      stroke: #e6e6df;
      stroke-width: 1;
    }
    .base {
      stroke: #b9b9b1;
      stroke-width: 1;
    }
    .eje {
      font-family: var(--mono);
      font-size: 10px;
      fill: var(--gris);
    }
    .zona {
      fill: transparent;
    }
    .marca {
      fill: var(--tinta);
      transition: fill 0.12s ease;
    }
    .cero {
      fill: #c9c9c1;
    }
    .columna {
      outline: none;
      cursor: default;
    }
    .columna.activa .marca {
      fill: var(--ganga);
    }
    .columna.activa .zona {
      fill: rgba(20, 22, 26, 0.04);
    }
    .tooltip {
      position: absolute;
      top: 0;
      transform: translateX(8px);
      display: flex;
      flex-direction: column;
      gap: 2px;
      background: #fff;
      border: 1.5px solid var(--tinta);
      border-radius: 9px;
      padding: 7px 10px;
      font-size: 12px;
      pointer-events: none;
      white-space: nowrap;
      box-shadow: 0 6px 16px rgba(20, 22, 26, 0.14);
    }
    .tooltip.a-la-izquierda {
      transform: translateX(calc(-100% - 8px));
    }
    .tooltip .detalle {
      color: var(--gris);
      font-size: 11px;
    }
  `,
})
export class SerieDias {
  readonly puntos = input.required<PuntoSerie[]>();
  readonly titulo = input('Ventas por periodo');

  readonly moneda = moneda;
  readonly ancho = ANCHO;
  readonly alto = ALTO;
  readonly margen = MARGEN;
  readonly base = ALTO - MARGEN.abajo;
  readonly altoUtil = ALTO - MARGEN.arriba - MARGEN.abajo;
  readonly activa = signal<number | null>(null);

  private readonly tope = computed(() => topeLindo(Math.max(0, ...this.puntos().map((p) => p.valor))));

  readonly marcas = computed(() => {
    const tope = this.tope();
    return [0, 0.25, 0.5, 0.75, 1].map((f) => ({
      valor: tope * f,
      y: this.base - this.altoUtil * f,
      texto: this.abreviar(tope * f),
    }));
  });

  readonly columnas = computed(() => {
    const puntos = this.puntos();
    const n = Math.max(puntos.length, 1);
    const paso = (ANCHO - MARGEN.izquierda - MARGEN.derecha) / n;
    // Marcas finas: la columna ocupa dos tercios del paso, con tope de 26 px.
    const w = Math.min(26, Math.max(3, paso * 0.66));
    const cadaCuantos = Math.ceil(n / 10);
    const tope = this.tope();
    return puntos.map((p, i) => {
      const x0 = MARGEN.izquierda + paso * i;
      const x = x0 + (paso - w) / 2;
      const h = Math.max(0, (p.valor / tope) * this.altoUtil);
      const y = this.base - h;
      const r = Math.min(4, w / 2, h);
      // Punta redondeada arriba y base recta apoyada en el eje.
      const forma = `M${x},${this.base} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${this.base} Z`;
      return { ...p, x0, x, w, paso, forma, rotulo: i % cadaCuantos === 0 };
    });
  });

  readonly tooltip = computed(() => {
    const i = this.activa();
    const c = i === null ? null : this.columnas()[i];
    return c ? { ...c, izquierda: ((c.x + c.w) / ANCHO) * 100 } : null;
  });

  private abreviar(valor: number): string {
    if (valor >= 1000) return `${(valor / 1000).toLocaleString('es-BO', { maximumFractionDigits: 1 })} mil`;
    return valor.toLocaleString('es-BO', { maximumFractionDigits: 0 });
  }
}
