import { Component, inject } from '@angular/core';

import { SucursalActual } from '../../core/sucursal-actual';

/** Selector de la sucursal de trabajo. Uso: `<app-selector-sucursal />`. */
@Component({
  selector: 'app-selector-sucursal',
  template: `
    <label class="selector">
      <span class="ceja">Sucursal</span>
      <select
        class="campo"
        [disabled]="sucursal.sucursales().length === 0"
        (change)="sucursal.elegir(+$any($event.target).value)"
      >
        @for (s of sucursal.sucursales(); track s.id) {
          <option [value]="s.id" [selected]="s.id === sucursal.id()">
            {{ s.nombre }}{{ s.id === sucursal.asignadaId() ? ' · tu sucursal' : '' }}
          </option>
        } @empty {
          <option>{{ sucursal.cargando() ? 'Cargando…' : 'Sin sucursales' }}</option>
        }
      </select>
    </label>
  `,
  styles: `
    .selector {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    select {
      width: auto;
      min-width: 190px;
    }
  `,
})
export class SelectorSucursal {
  readonly sucursal = inject(SucursalActual);

  constructor() {
    this.sucursal.cargar();
  }
}
