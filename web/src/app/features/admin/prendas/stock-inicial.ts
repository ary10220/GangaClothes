import { Component, computed, input, model } from '@angular/core';

/** Una sucursal del editor. Los numeros se guardan como texto, tal como se escriben. */
export interface FilaStock {
  sucursal_id: number;
  sucursal: string;
  cargar: boolean;
  cantidad: string;
  minimo: string;
  maximo: string;
}

/** Linea que espera el backend (prendas/router.py `StockInicialIn`). */
export interface LineaStock {
  sucursal_id: number;
  cantidad: number;
  stock_minimo: number;
  stock_maximo: number;
}

const ENTERO = /^\d+$/;

export function filasStock(sucursales: { id: number; nombre: string }[]): FilaStock[] {
  return sucursales.map((s) => ({
    sucursal_id: s.id,
    sucursal: s.nombre,
    cargar: false,
    cantidad: '',
    minimo: '0',
    maximo: '0',
  }));
}

/** Problema de cada sucursal marcada, por id. Vacio si todo esta bien. */
export function erroresStock(filas: FilaStock[]): Record<number, string> {
  const errores: Record<number, string> = {};
  for (const f of filas) {
    if (!f.cargar) continue;
    if (!ENTERO.test(f.cantidad.trim())) errores[f.sucursal_id] = 'Indica la cantidad (entero desde 0).';
    else if (!ENTERO.test(f.minimo.trim()) || !ENTERO.test(f.maximo.trim())) {
      errores[f.sucursal_id] = 'Minimo y maximo: enteros desde 0.';
    } else if (Number(f.maximo) > 0 && Number(f.minimo) > Number(f.maximo)) {
      errores[f.sucursal_id] = 'El minimo no puede superar al maximo.';
    }
  }
  return errores;
}

export function lineasStock(filas: FilaStock[]): LineaStock[] {
  return filas
    .filter((f) => f.cargar)
    .map((f) => ({
      sucursal_id: f.sucursal_id,
      cantidad: Number(f.cantidad),
      stock_minimo: Number(f.minimo),
      stock_maximo: Number(f.maximo),
    }));
}

/**
 * Editor del stock inicial por sucursal: se marca la sucursal y se escribe la
 * cantidad con su minimo y maximo. Uso: `<app-stock-inicial [(filas)]="filas" />`.
 */
@Component({
  selector: 'app-stock-inicial',
  template: `
    @if (filas().length === 0) {
      <p class="vacio-stock">No hay sucursales disponibles para cargar stock.</p>
    } @else {
      <div class="marco-tabla">
        <table>
          <thead>
            <tr>
              <th>Sucursal</th>
              <th class="num">Cantidad</th>
              <th class="num">Minimo</th>
              <th class="num">Maximo</th>
            </tr>
          </thead>
          <tbody>
            @for (f of filas(); track f.sucursal_id; let i = $index) {
              <tr [class.apagada]="!f.cargar">
                <td>
                  <label class="marcar">
                    <input
                      type="checkbox"
                      [checked]="f.cargar"
                      (change)="cambiar(i, 'cargar', $any($event.target).checked)"
                    />
                    {{ f.sucursal }}
                  </label>
                  @if (mostrarErrores() && errores()[f.sucursal_id]; as error) {
                    <span class="ayuda-error">{{ error }}</span>
                  }
                </td>
                @for (campo of campos; track campo) {
                  <td class="num">
                    <input
                      type="number"
                      min="0"
                      step="1"
                      class="campo"
                      [class.invalido]="mostrarErrores() && errores()[f.sucursal_id]"
                      [disabled]="!f.cargar"
                      [placeholder]="campo === 'cantidad' ? '0' : ''"
                      [value]="f[campo]"
                      [attr.aria-label]="campo + ' en ' + f.sucursal"
                      (input)="cambiar(i, campo, $any($event.target).value)"
                    />
                  </td>
                }
              </tr>
            }
          </tbody>
        </table>
      </div>
    }
  `,
  styles: `
    table {
      font-size: 12px;
    }
    th,
    td {
      padding: 6px 8px;
    }
    .num {
      text-align: right;
      width: 92px;
    }
    .campo {
      padding: 6px 8px;
      text-align: right;
    }
    .marcar {
      display: flex;
      align-items: center;
      gap: 7px;
      font-weight: 600;
      cursor: pointer;
    }
    .apagada .marcar {
      font-weight: 400;
      color: var(--gris);
    }
    .ayuda-error {
      display: block;
    }
    .vacio-stock {
      font-size: 12px;
      color: var(--gris);
    }
  `,
})
export class StockInicial {
  readonly filas = model.required<FilaStock[]>();
  readonly mostrarErrores = input(false);
  readonly errores = computed(() => erroresStock(this.filas()));
  readonly campos = ['cantidad', 'minimo', 'maximo'] as const;

  cambiar(indice: number, campo: 'cargar' | 'cantidad' | 'minimo' | 'maximo', valor: string | boolean): void {
    this.filas.update((filas) => filas.map((f, i) => (i === indice ? { ...f, [campo]: valor } : f)));
  }
}
