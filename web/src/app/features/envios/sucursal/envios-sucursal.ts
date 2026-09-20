import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { SucursalActual } from '../../../core/sucursal-actual';
import { Envio, EstadoEnvio, claseEstado } from '../../../shared/entrega/envio';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaLocal, moneda } from '../../../shared/formato';
import { Mapa, PuntoMapa } from '../../../shared/mapa/mapa';
import { SelectorSucursal } from '../../../shared/sucursal/selector-sucursal';

type FiltroEnvio = 'activos' | EstadoEnvio | 'todos';
/** Las transiciones que el encargado puede disparar, tal cual las nombra la API. */
type Accion = 'asignar' | 'en-camino' | 'entregar' | 'cancelar';

const FILTROS: OpcionFiltro<FiltroEnvio>[] = [
  { valor: 'activos', etiqueta: 'Por despachar' },
  { valor: 'pendiente', etiqueta: 'Pendientes' },
  { valor: 'asignado', etiqueta: 'Asignados' },
  { valor: 'en_camino', etiqueta: 'En camino' },
  { valor: 'entregado', etiqueta: 'Entregados' },
  { valor: 'cancelado', etiqueta: 'Cancelados' },
  { valor: 'todos', etiqueta: 'Todos' },
];

const ACTIVOS: EstadoEnvio[] = ['pendiente', 'asignado', 'en_camino'];

/**
 * CU29: envios a domicilio de la sucursal.
 *
 * El encargado ve los pedidos ya cobrados que hay que llevar, con su destino en
 * el mapa, y los va moviendo de estado:
 *
 *   pendiente --Asignar--> asignado --En camino--> en_camino --Entregar--> entregado
 *
 * Cancelar corta la entrega a domicilio en cualquiera de esos tres estados. No
 * anula la venta ni devuelve stock: la compra ya se cobro y salio del
 * inventario; lo que queda es coordinar el retiro con el cliente.
 */
@Component({
  selector: 'app-envios-sucursal',
  imports: [SelectorEstado, SelectorSucursal, Mapa],
  templateUrl: './envios-sucursal.html',
  styleUrl: './envios-sucursal.css',
  host: { '(document:keydown.escape)': 'cerrarModal()' },
})
export class EnviosSucursal {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);
  readonly sucursal = inject(SucursalActual);

  readonly fecha = fechaLocal;
  readonly moneda = moneda;
  readonly claseEstado = claseEstado;

  readonly envios = signal<Envio[]>([]);
  readonly cargando = signal(false);
  readonly errorCarga = signal<string | null>(null);
  readonly filtro = signal<FiltroEnvio>('activos');
  private pedido = 0;

  /** Envio con una accion en curso, para deshabilitar solo sus botones. */
  readonly enProceso = signal<number | null>(null);

  // ---- modal de asignar repartidor ----
  readonly aAsignar = signal<Envio | null>(null);
  readonly repartidor = signal('');
  // ---- modal de cancelar ----
  readonly aCancelar = signal<Envio | null>(null);
  readonly motivo = signal('');
  readonly errorModal = signal<string | null>(null);

  readonly puedeEditar = computed(() => this.sesion.permisos().includes('envios:editar'));

  readonly opciones = computed<OpcionFiltro<FiltroEnvio>[]>(() =>
    FILTROS.map((f) => ({ ...f, etiqueta: `${f.etiqueta} (${this.enFiltro(f.valor).length})` })),
  );

  readonly visibles = computed(() => this.enFiltro(this.filtro()));

  /** Los pedidos que todavia hay que llevar: son los que van al mapa. */
  readonly porDespachar = computed(() => this.envios().filter((e) => ACTIVOS.includes(e.estado)));

  /**
   * El mapa de la sucursal: su propio punto y el destino de cada pedido que
   * falta entregar, para ver de un vistazo como conviene armar el recorrido.
   */
  readonly puntos = computed<PuntoMapa[]>(() => {
    const pendientes = this.porDespachar();
    const puntos: PuntoMapa[] = [];
    const origen = pendientes[0]?.sucursal ?? this.envios()[0]?.sucursal ?? null;
    if (origen && origen.latitud !== null && origen.longitud !== null) {
      puntos.push({
        latitud: origen.latitud,
        longitud: origen.longitud,
        tipo: 'origen',
        titulo: origen.nombre,
        detalle: 'sale desde aqui',
      });
    }
    for (const envio of pendientes) {
      puntos.push({
        latitud: envio.latitud,
        longitud: envio.longitud,
        tipo: 'pendiente',
        titulo: envio.direccion,
        detalle:
          `${envio.etiqueta_estado} · ${envio.distancia_km} km` +
          (envio.repartidor ? ` · ${envio.repartidor}` : ''),
      });
    }
    return puntos;
  });

  readonly pie = computed(() => {
    const lista = this.visibles();
    const cobrado = lista.reduce((suma, e) => suma + e.costo_envio, 0);
    const nombre = lista.length === 1 ? 'envio' : 'envios';
    return cobrado > 0
      ? `${lista.length} ${nombre} · Bs ${moneda(cobrado)} cobrados de reparto`
      : `${lista.length} ${nombre}`;
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
      this.envios.set([]);
      return;
    }
    this.cargando.set(true);
    this.http.get<Envio[]>(`${API_URL}/envios`, { params: { sucursal_id: sucursalId } }).subscribe({
      next: (filas) => {
        if (pedido !== this.pedido) return;
        this.envios.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.errorCarga.set(mensajeDeError(err, 'No se pudieron cargar los envios.'));
        this.cargando.set(false);
      },
    });
  }

  private enFiltro(filtro: FiltroEnvio): Envio[] {
    const todos = this.envios();
    if (filtro === 'todos') return todos;
    if (filtro === 'activos') return todos.filter((e) => ACTIVOS.includes(e.estado));
    return todos.filter((e) => e.estado === filtro);
  }

  // --------------------------------------------------------------- acciones
  pedirAsignar(envio: Envio): void {
    this.errorModal.set(null);
    this.repartidor.set(envio.repartidor ?? '');
    this.aAsignar.set(envio);
  }

  confirmarAsignar(): void {
    const envio = this.aAsignar();
    const nombre = this.repartidor().trim();
    if (!envio) return;
    if (nombre.length < 3) {
      this.errorModal.set('Escribe el nombre del repartidor.');
      return;
    }
    this.ejecutar(
      envio,
      'asignar',
      (e) => `Envio #${e.id} asignado a ${e.repartidor}: ya puede salir hacia ${e.direccion}.`,
      { repartidor: nombre },
    );
  }

  enCamino(envio: Envio): void {
    this.ejecutar(
      envio,
      'en-camino',
      (e) => `${e.repartidor ?? 'El repartidor'} salio con el envio #${e.id} hacia ${e.direccion}.`,
    );
  }

  entregar(envio: Envio): void {
    this.ejecutar(
      envio,
      'entregar',
      (e) => `Envio #${e.id} entregado a ${e.cliente?.nombre ?? 'el cliente'} en ${e.direccion}.`,
    );
  }

  pedirCancelar(envio: Envio): void {
    this.errorModal.set(null);
    this.motivo.set('');
    this.aCancelar.set(envio);
  }

  confirmarCancelar(): void {
    const envio = this.aCancelar();
    if (!envio) return;
    this.ejecutar(envio, 'cancelar', (e) => `Envio #${e.id} cancelado. La compra sigue cobrada.`, {
      motivo: this.motivo().trim() || null,
    });
  }

  private ejecutar(
    envio: Envio,
    accion: Accion,
    mensaje: (e: Envio) => string,
    cuerpo: Record<string, unknown> = {},
  ): void {
    this.enProceso.set(envio.id);
    this.errorModal.set(null);
    this.http.post<Envio>(`${API_URL}/envios/${envio.id}/${accion}`, cuerpo).subscribe({
      next: (actualizado) => {
        this.enProceso.set(null);
        this.cerrarModal();
        this.avisos.ok(mensaje(actualizado));
        this.recargar();
      },
      error: (err: HttpErrorResponse) => {
        this.enProceso.set(null);
        const texto = mensajeDeError(err, `No se pudo ${accion.replace('-', ' ')} el envio #${envio.id}.`);
        if (this.aAsignar() || this.aCancelar()) this.errorModal.set(texto);
        else this.avisos.error(texto);
        // Un 400 suele ser un envio que otra persona ya movio de estado.
        if (err.status === 400) this.recargar();
      },
    });
  }

  cerrarModal(): void {
    if (this.enProceso() !== null) return;
    this.aAsignar.set(null);
    this.aCancelar.set(null);
    this.errorModal.set(null);
  }

  // ----------------------------------------------------------- presentacion
  unidades(envio: Envio): number {
    return envio.prendas.reduce((suma, p) => suma + p.cantidad, 0);
  }

  /** El pedido ya paso su hora estimada de entrega y todavia no llego. */
  atrasado(envio: Envio): boolean {
    if (!envio.fecha_estimada || !ACTIVOS.includes(envio.estado)) return false;
    return new Date(envio.fecha_estimada).getTime() < Date.now();
  }
}
