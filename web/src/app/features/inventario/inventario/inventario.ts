import { HttpClient } from '@angular/common/http';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import {
  AbstractControl,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { SucursalActual } from '../../../core/sucursal-actual';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { SelectorSucursal } from '../../../shared/sucursal/selector-sucursal';

/** Una fila de GET /api/inventario (backend: inventario/service.py `_fila_inventario`). */
export interface FilaInventario {
  id: number;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  color_hex: string | null;
  sucursal_id: number;
  sucursal: string;
  cantidad: number;
  cantidad_reservada: number;
  disponible: number;
  stock_minimo: number;
  stock_maximo: number;
  bajo_minimo: boolean;
}

type FiltroStock = 'todas' | 'bajo';

const FILTROS: OpcionFiltro<FiltroStock>[] = [
  { valor: 'todas', etiqueta: 'Todas' },
  { valor: 'bajo', etiqueta: 'Bajo el minimo' },
];

const ENTERO = /^\d+$/;

function minimoHastaMaximo(grupo: AbstractControl): ValidationErrors | null {
  const minimo = grupo.get('stock_minimo')?.value;
  const maximo = grupo.get('stock_maximo')?.value;
  if (minimo === null || minimo === '' || maximo === null || maximo === '') return null;
  return Number(minimo) > Number(maximo) ? { minimoMayor: true } : null;
}

/**
 * CU11: stock de la sucursal con sus minimos y maximos.
 * La cantidad no se edita aca: cambia solo con movimientos (CU12) y compras (CU10).
 */
@Component({
  selector: 'app-inventario',
  imports: [ReactiveFormsModule, RouterLink, SelectorEstado, SelectorSucursal],
  templateUrl: './inventario.html',
  styleUrl: './inventario.css',
  host: { '(document:keydown.escape)': 'cerrarModal()' },
})
export class Inventario {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);
  readonly sucursal = inject(SucursalActual);

  readonly filtros = FILTROS;

  // ---- listado ----
  readonly filas = signal<FilaInventario[]>([]);
  readonly alertas = signal(0);
  readonly cargando = signal(false);
  readonly errorCarga = signal<string | null>(null);
  readonly filtro = signal<FiltroStock>('todas');
  readonly busqueda = signal('');
  /** Descarta respuestas viejas si se cambia de sucursal antes de que lleguen. */
  private pedido = 0;

  // ---- edicion de limites ----
  readonly editando = signal<FilaInventario | null>(null);
  readonly guardando = signal(false);
  readonly errorLimites = signal<string | null>(null);
  formLimites: FormGroup = this.fb.group({});

  readonly puedeEditar = computed(() => this.sesion.permisos().includes('inventario:editar'));
  readonly puedeCrear = computed(() => this.sesion.permisos().includes('inventario:crear'));

  readonly enFiltro = computed(() =>
    this.filtro() === 'bajo' ? this.filas().filter((f) => f.bajo_minimo) : this.filas(),
  );

  readonly visibles = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    if (!texto) return this.enFiltro();
    return this.enFiltro().filter((f) =>
      [f.sku, f.prenda, f.talla, f.color].join(' ').toLowerCase().includes(texto),
    );
  });

  readonly pie = computed(() => {
    const total = this.enFiltro().length;
    const mostradas = this.visibles().length;
    const nombre = total === 1 ? 'variante' : 'variantes';
    return mostradas === total ? `${total} ${nombre}` : `${mostradas} de ${total} ${nombre}`;
  });

  constructor() {
    effect(() => {
      const id = this.sucursal.id();
      untracked(() => this.cargar(id));
    });
  }

  // ------------------------------------------------------------------ carga
  recargar(): void {
    this.cargar(this.sucursal.id());
  }

  private cargar(sucursalId: number | null): void {
    const pedido = ++this.pedido;
    this.errorCarga.set(null);
    if (sucursalId === null) {
      this.filas.set([]);
      this.alertas.set(0);
      return;
    }

    this.cargando.set(true);
    const params = { sucursal_id: sucursalId };
    forkJoin({
      filas: this.http.get<FilaInventario[]>(`${API_URL}/inventario`, { params }),
      alertas: this.http.get<FilaInventario[]>(`${API_URL}/inventario/alertas`, { params }),
    }).subscribe({
      next: ({ filas, alertas }) => {
        if (pedido !== this.pedido) return;
        this.filas.set(filas);
        this.alertas.set(alertas.length);
        this.cargando.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.errorCarga.set(mensajeDeError(err, 'No se pudo cargar el inventario.'));
        this.cargando.set(false);
      },
    });
  }

  // ------------------------------------------------------- minimo y maximo
  abrirLimites(fila: FilaInventario): void {
    this.errorLimites.set(null);
    const entero = [Validators.required, Validators.min(0), Validators.pattern(ENTERO)];
    this.formLimites = this.fb.group(
      { stock_minimo: [fila.stock_minimo, entero], stock_maximo: [fila.stock_maximo, entero] },
      { validators: minimoHastaMaximo },
    );
    this.editando.set(fila);
  }

  invalido(campo: string): boolean {
    const control = this.formLimites.get(campo);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  /** El error del grupo se muestra en cuanto se toco cualquiera de los dos campos. */
  minimoMayor(): boolean {
    const tocado = ['stock_minimo', 'stock_maximo'].some((c) => {
      const control = this.formLimites.get(c);
      return !!control && (control.dirty || control.touched);
    });
    return tocado && this.formLimites.hasError('minimoMayor');
  }

  guardarLimites(): void {
    const fila = this.editando();
    if (!fila) return;
    if (this.formLimites.invalid) {
      this.formLimites.markAllAsTouched();
      return;
    }
    this.errorLimites.set(null);
    this.guardando.set(true);

    const crudo = this.formLimites.getRawValue();
    const datos = { stock_minimo: Number(crudo.stock_minimo), stock_maximo: Number(crudo.stock_maximo) };

    this.http.put<FilaInventario>(`${API_URL}/inventario/${fila.id}`, datos).subscribe({
      next: (actualizada) => {
        this.guardando.set(false);
        this.editando.set(null);
        this.avisos.ok(
          `Limites de ${actualizada.sku} guardados: minimo ${actualizada.stock_minimo}, ` +
            `maximo ${actualizada.stock_maximo}.` +
            (actualizada.bajo_minimo ? ' La variante queda bajo el minimo.' : ''),
        );
        this.recargar();
      },
      error: (err) => {
        this.guardando.set(false);
        this.errorLimites.set(mensajeDeError(err, 'No se pudieron guardar los limites.'));
      },
    });
  }

  cerrarModal(): void {
    this.editando.set(null);
  }

  // ----------------------------------------------------------- presentacion
  textoEstado(fila: FilaInventario): string {
    if (fila.disponible <= 0) return 'Agotado';
    return fila.bajo_minimo ? 'Stock bajo' : 'OK';
  }

  hex(valor: string | null): string {
    return /^#[0-9a-f]{6}$/i.test(valor ?? '') ? valor! : '#CCCCCC';
  }
}
