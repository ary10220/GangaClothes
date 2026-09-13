import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { forkJoin } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { SucursalActual } from '../../../core/sucursal-actual';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaLocal } from '../../../shared/formato';
import { SelectorSucursal } from '../../../shared/sucursal/selector-sucursal';
import { FilaInventario } from '../inventario/inventario';

type TipoMovimiento = 'ingreso' | 'salida' | 'ajuste' | 'devolucion';
type FiltroTipo = 'todos' | TipoMovimiento;

/** Una fila de GET /api/inventario/movimientos (backend: `_fila_movimiento`). */
interface Movimiento {
  id: number;
  fecha: string | null;
  tipo: TipoMovimiento;
  cantidad: number;
  motivo: string | null;
  variante_id: number;
  sku: string;
  prenda: string;
  sucursal_id: number;
  sucursal: string;
  usuario_id: number | null;
  usuario: string | null;
}

interface ResultadoMovimiento {
  movimiento: Movimiento;
  stock_anterior: number;
  stock_actual: number;
  inventario: FilaInventario;
}

const TIPOS: { valor: TipoMovimiento; etiqueta: string; ayuda: string }[] = [
  { valor: 'ingreso', etiqueta: 'Ingreso', ayuda: 'Suma unidades al stock.' },
  { valor: 'salida', etiqueta: 'Salida', ayuda: 'Resta unidades del disponible: merma, traspaso o uso interno.' },
  { valor: 'ajuste', etiqueta: 'Ajuste', ayuda: 'Fija el stock en el total contado en el conteo fisico.' },
  { valor: 'devolucion', etiqueta: 'Devolucion', ayuda: 'Suma unidades que vuelven de un cliente.' },
];

const FILTROS: OpcionFiltro<FiltroTipo>[] = [
  { valor: 'todos', etiqueta: 'Todos' },
  { valor: 'ingreso', etiqueta: 'Ingresos' },
  { valor: 'salida', etiqueta: 'Salidas' },
  { valor: 'ajuste', etiqueta: 'Ajustes' },
  { valor: 'devolucion', etiqueta: 'Devoluciones' },
];

/** El backend devuelve como mucho los ultimos 200 movimientos. */
const LIMITE_HISTORIAL = 200;

/**
 * CU12: historial de movimientos de la sucursal y registro de ingresos,
 * salidas, ajustes y devoluciones. Las reglas de stock las valida el backend;
 * la pantalla adelanta las mismas cuentas para avisar antes de enviar.
 */
@Component({
  selector: 'app-movimientos',
  imports: [ReactiveFormsModule, SelectorEstado, SelectorSucursal],
  templateUrl: './movimientos.html',
  styleUrl: './movimientos.css',
  host: { '(document:keydown.escape)': 'cerrarModal()' },
})
export class Movimientos {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);
  private router = inject(Router);
  private ruta = inject(ActivatedRoute);
  readonly sucursal = inject(SucursalActual);

  /** `?registrar=1` abre el formulario al entrar (boton de la pantalla de inventario). */
  readonly registrar = input<string>();

  readonly tipos = TIPOS;
  readonly filtros = FILTROS;

  // ---- datos ----
  readonly variantes = signal<FilaInventario[]>([]);
  readonly movimientos = signal<Movimiento[]>([]);
  readonly cargando = signal(false);
  readonly cargandoHistorial = signal(false);
  readonly errorCarga = signal<string | null>(null);
  readonly varianteFiltro = signal<number | null>(null);
  readonly tipoFiltro = signal<FiltroTipo>('todos');
  private pedido = 0;

  // ---- formulario ----
  readonly modalAbierto = signal(false);
  readonly guardando = signal(false);
  readonly intentoGuardar = signal(false);
  readonly errorServidor = signal<string | null>(null);
  readonly formMov = this.fb.nonNullable.group({
    tipo: 'ingreso' as TipoMovimiento,
    variante_id: ['', Validators.required],
    cantidad: [''],
    motivo: ['', Validators.maxLength(200)],
  });
  private readonly valores = toSignal(this.formMov.valueChanges, { initialValue: this.formMov.getRawValue() });

  readonly puedeRegistrar = computed(() => this.sesion.permisos().includes('inventario:editar'));

  readonly visibles = computed(() =>
    this.tipoFiltro() === 'todos'
      ? this.movimientos()
      : this.movimientos().filter((m) => m.tipo === this.tipoFiltro()),
  );

  readonly pie = computed(() => {
    const total = this.movimientos().length;
    const mostrados = this.visibles().length;
    const nombre = total === 1 ? 'movimiento' : 'movimientos';
    const texto = mostrados === total ? `${total} ${nombre}` : `${mostrados} de ${total} ${nombre}`;
    return total >= LIMITE_HISTORIAL ? `${texto} · solo los ${LIMITE_HISTORIAL} mas recientes` : texto;
  });

  // ---- cuentas del formulario ----
  readonly tipoElegido = computed(() => TIPOS.find((t) => t.valor === this.valores().tipo) ?? TIPOS[0]);
  readonly varianteElegida = computed(
    () => this.variantes().find((v) => v.variante_id === Number(this.valores().variante_id)) ?? null,
  );
  private readonly cantidad = computed(() => {
    const texto = String(this.valores().cantidad ?? '').trim();
    return /^\d+$/.test(texto) ? Number(texto) : null;
  });

  /** Mismas reglas que `_aplicar` en el backend, con los numeros de la sucursal. */
  readonly errorCantidad = computed<string | null>(() => {
    const texto = String(this.valores().cantidad ?? '').trim();
    const tipo = this.valores().tipo;
    const v = this.varianteElegida();
    const n = this.cantidad();
    if (texto === '') return this.intentoGuardar() ? 'Ingresa la cantidad.' : null;
    if (n === null) return 'Ingresa un numero entero, sin signo.';
    if (n === 0 && tipo !== 'ajuste') return 'La cantidad debe ser mayor que cero.';
    if (!v) return null;
    if (tipo === 'salida' && n > v.disponible) {
      return (
        `No hay stock suficiente: se piden ${n} y solo hay ${v.disponible} disponibles ` +
        `(${v.cantidad} en stock menos ${v.cantidad_reservada} reservados).`
      );
    }
    if (tipo === 'ajuste' && n < v.cantidad_reservada) {
      return `El ajuste deja ${n} unidades pero hay ${v.cantidad_reservada} reservadas.`;
    }
    return null;
  });

  /** Si el backend rechazo con el mismo texto que ya calcula la pantalla, se muestra una sola vez. */
  readonly errorCantidadVisible = computed(() => {
    const local = this.errorCantidad();
    const servidor = this.errorServidor();
    const sinPunto = (texto: string) => texto.trim().replace(/\.$/, '');
    return local && servidor && sinPunto(local) === sinPunto(servidor) ? null : local;
  });

  readonly vistaPrevia = computed(() => {
    const v = this.varianteElegida();
    const n = this.cantidad();
    if (!v || n === null || this.errorCantidad()) return null;
    const tipo = this.valores().tipo;
    const despues = tipo === 'ajuste' ? n : tipo === 'salida' ? v.cantidad - n : v.cantidad + n;
    const disponible = despues - v.cantidad_reservada;
    return { antes: v.cantidad, despues, disponible, bajoMinimo: disponible <= v.stock_minimo };
  });

  constructor() {
    effect(() => {
      const id = this.sucursal.id();
      untracked(() => {
        this.varianteFiltro.set(null);
        this.cargar(id);
      });
    });
    effect(() => {
      if (!this.registrar() || !this.puedeRegistrar()) return;
      untracked(() => {
        this.abrirRegistro();
        // Sin esto, recargar la pagina volveria a abrir el formulario.
        this.router.navigate([], {
          relativeTo: this.ruta,
          queryParams: { registrar: null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        });
      });
    });
    // El rechazo del servidor queda viejo en cuanto se cambia el formulario.
    effect(() => {
      this.valores();
      untracked(() => this.errorServidor.set(null));
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
      this.variantes.set([]);
      this.movimientos.set([]);
      return;
    }
    this.cargando.set(true);
    forkJoin({
      variantes: this.http.get<FilaInventario[]>(`${API_URL}/inventario`, { params: { sucursal_id: sucursalId } }),
      movimientos: this.pedirHistorial(sucursalId),
    }).subscribe({
      next: ({ variantes, movimientos }) => {
        if (pedido !== this.pedido) return;
        this.variantes.set(variantes);
        this.movimientos.set(movimientos);
        this.cargando.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.errorCarga.set(mensajeDeError(err, 'No se pudo cargar el historial de movimientos.'));
        this.cargando.set(false);
      },
    });
  }

  filtrarVariante(valor: string): void {
    this.varianteFiltro.set(valor ? Number(valor) : null);
    const sucursalId = this.sucursal.id();
    if (sucursalId === null) return;
    const pedido = ++this.pedido;
    this.cargandoHistorial.set(true);
    this.pedirHistorial(sucursalId).subscribe({
      next: (movimientos) => {
        if (pedido !== this.pedido) return;
        this.movimientos.set(movimientos);
        this.cargandoHistorial.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.errorCarga.set(mensajeDeError(err, 'No se pudo filtrar el historial.'));
        this.cargandoHistorial.set(false);
      },
    });
  }

  private pedirHistorial(sucursalId: number) {
    const params: Record<string, number> = { sucursal_id: sucursalId };
    const variante = this.varianteFiltro();
    if (variante !== null) params['variante_id'] = variante;
    return this.http.get<Movimiento[]>(`${API_URL}/inventario/movimientos`, { params });
  }

  // ------------------------------------------------------------- registro
  abrirRegistro(): void {
    this.errorServidor.set(null);
    this.intentoGuardar.set(false);
    const filtrada = this.varianteFiltro();
    this.formMov.reset({
      tipo: 'ingreso',
      variante_id: filtrada === null ? '' : String(filtrada),
      cantidad: '',
      motivo: '',
    });
    this.modalAbierto.set(true);
  }

  elegirTipo(tipo: TipoMovimiento): void {
    this.formMov.controls.tipo.setValue(tipo);
  }

  varianteInvalida(): boolean {
    const control = this.formMov.controls.variante_id;
    return control.invalid && (control.touched || this.intentoGuardar());
  }

  guardar(): void {
    this.intentoGuardar.set(true);
    this.formMov.markAllAsTouched();
    if (this.formMov.invalid || this.errorCantidad() || this.cantidad() === null) return;

    const crudo = this.formMov.getRawValue();
    const datos = {
      tipo: crudo.tipo,
      variante_id: Number(crudo.variante_id),
      sucursal_id: this.sucursal.id(),
      cantidad: this.cantidad(),
      motivo: crudo.motivo.trim() || null,
    };

    this.errorServidor.set(null);
    this.guardando.set(true);
    this.http.post<ResultadoMovimiento>(`${API_URL}/inventario/movimientos`, datos).subscribe({
      next: (r) => {
        this.guardando.set(false);
        this.modalAbierto.set(false);
        const tipo = TIPOS.find((t) => t.valor === r.movimiento.tipo)?.etiqueta ?? r.movimiento.tipo;
        this.avisos.ok(
          `${tipo} registrado en ${r.movimiento.sku}: stock ${r.stock_anterior} → ${r.stock_actual}.` +
            (r.inventario.bajo_minimo ? ' La variante queda bajo el minimo.' : ''),
        );
        this.recargar();
      },
      error: (err: HttpErrorResponse) => {
        this.guardando.set(false);
        this.errorServidor.set(mensajeDeError(err, 'No se pudo registrar el movimiento.'));
        // Un 400 suele ser stock que cambio mientras el formulario estaba abierto:
        // se refrescan las cantidades para que la vista previa muestre las reales.
        if (err.status === 400) this.refrescarVariantes();
      },
    });
  }

  private refrescarVariantes(): void {
    const sucursalId = this.sucursal.id();
    if (sucursalId === null) return;
    this.http
      .get<FilaInventario[]>(`${API_URL}/inventario`, { params: { sucursal_id: sucursalId } })
      .subscribe({ next: (filas) => this.variantes.set(filas) });
  }

  cerrarModal(): void {
    this.modalAbierto.set(false);
  }

  // ----------------------------------------------------------- presentacion
  etiquetaTipo(tipo: TipoMovimiento): string {
    return TIPOS.find((t) => t.valor === tipo)?.etiqueta ?? tipo;
  }

  claseTipo(tipo: TipoMovimiento): string {
    return tipo === 'salida' ? 'bajo' : tipo === 'ajuste' ? 'rosa' : 'ok';
  }

  cantidadConSigno(m: Movimiento): string {
    if (m.tipo === 'salida') return `−${m.cantidad}`;
    if (m.tipo === 'ajuste') return `= ${m.cantidad}`;
    return `+${m.cantidad}`;
  }

  etiquetaVariante(fila: { sku: string; prenda: string; talla: string; color: string }): string {
    return `${fila.sku} · ${fila.prenda} · ${fila.talla} · ${fila.color}`;
  }

  detalleVariante(m: Movimiento): string {
    const v = this.variantes().find((f) => f.variante_id === m.variante_id);
    return v ? `${v.prenda} · ${v.talla} · ${v.color}` : m.prenda;
  }

  fecha(iso: string | null): string {
    return fechaLocal(iso);
  }
}
