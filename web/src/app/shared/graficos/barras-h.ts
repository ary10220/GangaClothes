import { Component, computed, input } from '@angular/core';

export interface FilaBarra {
  etiqueta: string;
  valor: number;
  /** Texto del valor ya formateado ("Bs 1.234,50"). */
  texto: string;
  /** Dato secundario a la derecha ("38% · 12 ventas"). */
  detalle?: string;
  /** Color de la barra; sin el, el de la serie unica. */
  color?: string;
}

/**
 * Barras horizontales con el nombre y el valor escritos en cada fila: la
 * identidad nunca depende solo del color. Sin librerias: son divs.
 * Uso: `<app-barras-h [filas]="porSucursal()" />`.
 */
@Component({
  selector: 'app-barras-h',
  template: `
    <div class="barras" role="list">
      @for (f of medidas(); track f.etiqueta) {
        <div class="fila-barra" role="listitem" [attr.aria-label]="f.etiqueta + ': ' + f.texto" [title]="f.etiqueta + ' · ' + f.texto + (f.detalle ? ' · ' + f.detalle : '')">
          <div class="rotulo">
            <span class="nombre">{{ f.etiqueta }}</span>
            <span class="mono valor">{{ f.texto }}</span>
          </div>
          <div class="pista">
            <div class="barra" [style.width.%]="f.ancho" [style.background]="f.color || null"></div>
          </div>
          @if (f.detalle) {
            <div class="detalle">{{ f.detalle }}</div>
          }
        </div>
      } @empty {
        <p class="sin-datos">Sin datos en el periodo.</p>
      }
    </div>
  `,
  styles: `
    .barras {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .rotulo {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      font-size: 12.5px;
      margin-bottom: 4px;
    }
    .nombre {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .valor {
      font-weight: 700;
      white-space: nowrap;
    }
    .pista {
      height: 8px;
      background: #ecece5;
      border-radius: 4px;
      overflow: hidden;
    }
    .barra {
      height: 100%;
      min-width: 2px;
      background: var(--tinta);
      border-radius: 0 4px 4px 0;
      transition: width 0.35s ease;
    }
    .fila-barra:hover .pista {
      background: #e0e0d8;
    }
    .detalle {
      font-size: 11px;
      color: var(--gris);
      margin-top: 3px;
    }
    .sin-datos {
      font-size: 12.5px;
      color: var(--gris);
    }
  `,
})
export class BarrasH {
  readonly filas = input.required<FilaBarra[]>();

  readonly medidas = computed(() => {
    const maximo = Math.max(0, ...this.filas().map((f) => f.valor));
    return this.filas().map((f) => ({ ...f, ancho: maximo > 0 ? Math.max(0, (f.valor / maximo) * 100) : 0 }));
  });
}
