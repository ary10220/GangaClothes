import { Component, inject } from '@angular/core';

import { Notificaciones } from '../../core/notificaciones';

@Component({
  selector: 'app-avisos',
  template: `
    <div class="avisos">
      @for (aviso of notificaciones.avisos(); track aviso.id) {
        <div class="aviso" [class.error]="aviso.tipo === 'error'" (click)="notificaciones.cerrar(aviso.id)">
          <span class="icono">{{ aviso.tipo === 'error' ? '!' : '✓' }}</span>
          <span>{{ aviso.texto }}</span>
        </div>
      }
    </div>
  `,
  styles: `
    .aviso {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      background: #fff;
      border: 1.5px solid var(--ok);
      border-left-width: 5px;
      border-radius: 10px;
      padding: 11px 14px;
      font-size: 12.5px;
      line-height: 1.45;
      box-shadow: 0 8px 22px rgba(20, 22, 26, 0.16);
      cursor: pointer;
    }
    .aviso.error {
      border-color: var(--alerta);
    }
    .icono {
      font-family: var(--mono);
      font-weight: 700;
      color: var(--ok);
    }
    .aviso.error .icono {
      color: var(--alerta);
    }
  `,
})
export class Avisos {
  readonly notificaciones = inject(Notificaciones);
}
