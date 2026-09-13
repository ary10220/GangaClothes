import { Component, input, model } from '@angular/core';

import { FiltroEstado } from './estado';

export interface OpcionFiltro<T extends string = string> {
  valor: T;
  etiqueta: string;
}

const OPCIONES_ACTIVO: OpcionFiltro<FiltroEstado>[] = [
  { valor: 'activos', etiqueta: 'Activos' },
  { valor: 'inactivos', etiqueta: 'Inactivos' },
  { valor: 'todos', etiqueta: 'Todos' },
];

/**
 * Chips de filtro por estado.
 * Activo / archivado (por defecto): `<app-selector-estado [(valor)]="estado" />`.
 * Otros estados (stock, compras, reservas): `<app-selector-estado [(valor)]="filtro" [opciones]="OPCIONES" />`.
 */
@Component({
  selector: 'app-selector-estado',
  template: `
    <div class="filtro-estado" role="group" aria-label="Filtrar por estado">
      @for (opcion of opciones(); track opcion.valor) {
        <button type="button" class="chip" [class.on]="valor() === opcion.valor" (click)="valor.set(opcion.valor)">
          {{ opcion.etiqueta }}
        </button>
      }
    </div>
  `,
  styles: `
    .filtro-estado {
      display: flex;
    }
    .chip {
      font-family: inherit;
      margin: 0 6px 0 0;
    }
  `,
})
export class SelectorEstado<T extends string = FiltroEstado> {
  readonly valor = model.required<T>();
  readonly opciones = input<OpcionFiltro<T>[]>(OPCIONES_ACTIVO as unknown as OpcionFiltro<T>[]);
}
