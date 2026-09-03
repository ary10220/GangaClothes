import { Component, model } from '@angular/core';

import { FiltroEstado } from './estado';

const OPCIONES: { valor: FiltroEstado; etiqueta: string }[] = [
  { valor: 'activos', etiqueta: 'Activos' },
  { valor: 'inactivos', etiqueta: 'Inactivos' },
  { valor: 'todos', etiqueta: 'Todos' },
];

/** Los tres chips del filtro. Uso: `<app-selector-estado [(valor)]="estado" />`. */
@Component({
  selector: 'app-selector-estado',
  template: `
    <div class="filtro-estado" role="group" aria-label="Filtrar por estado">
      @for (opcion of opciones; track opcion.valor) {
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
export class SelectorEstado {
  readonly valor = model.required<FiltroEstado>();
  protected readonly opciones = OPCIONES;
}
