import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, effect, inject, signal, untracked } from '@angular/core';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { SucursalActual } from '../../../core/sucursal-actual';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaSinZona, instanteSinZona } from '../../../shared/formato';
import { SelectorSucursal } from '../../../shared/sucursal/selector-sucursal';

type EstadoReserva = 'pendiente' | 'preparada' | 'atendida' | 'cancelada' | 'expirada';
type FiltroReserva = 'activas' | EstadoReserva | 'todas';
type Accion = 'preparar' | 'atender' | 'expirar';

interface LineaReserva {
  id: number;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  cantidad: number;
  /** "reservado" mientras aparta stock; "liberado" cuando ya lo devolvio. */
  estado: 'reservado' | 'liberado';
}

/** GET /api/reservas (backend: reservas/service.py `_salida` con cliente). */
export interface ReservaSucursal {
  id: number;
  estado: EstadoReserva;
  fecha_creacion: string | null;
  fecha_hora_prueba: string | null;
  notas: string | null;
  sucursal_id: number;
  sucursal: string | null;
  unidades: number;
  detalle: LineaReserva[];
  cliente: { id: number; nombre: string | null; email: string | null; telefono: string | null };
}

const FILTROS: OpcionFiltro<FiltroReserva>[] = [
  { valor: 'activas', etiqueta: 'Activas' },
  { valor: 'pendiente', etiqueta: 'Pendientes' },
  { valor: 'preparada', etiqueta: 'Preparadas' },
  { valor: 'atendida', etiqueta: 'Atendidas' },
  { valor: 'cancelada', etiqueta: 'Canceladas' },
  { valor: 'expirada', etiqueta: 'Expiradas' },
  { valor: 'todas', etiqueta: 'Todas' },
];

const ACTIVAS: EstadoReserva[] = ['pendiente', 'preparada'];

/**
 * CU13: reservas de la sucursal para probarse prendas en tienda.
 * pendiente -> Preparar -> preparada -> Atender -> atendida; Expirar libera el
 * stock apartado cuando el cliente no vino.
 */
@Component({
  selector: 'app-reservas-sucursal',
  imports: [SelectorEstado, SelectorSucursal],
  templateUrl: './reservas-sucursal.html',
  styleUrl: './reservas-sucursal.css',
  host: { '(document:keydown.escape)': 'cerrarModal()' },
})
export class ReservasSucursal {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);
  readonly sucursal = inject(SucursalActual);

  readonly fecha = fechaSinZona;

  readonly reservas = signal<ReservaSucursal[]>([]);
  readonly cargando = signal(false);
  readonly errorCarga = signal<string | null>(null);
  readonly filtro = signal<FiltroReserva>('activas');
  private pedido = 0;

  /** Reserva sobre la que hay una accion en curso, para deshabilitar solo sus botones. */
  readonly enProceso = signal<number | null>(null);
  readonly aExpirar = signal<ReservaSucursal | null>(null);
  readonly errorExpirar = signal<string | null>(null);

  /** Se actualiza cada minuto para marcar las citas cuya hora ya paso. */
  private readonly ahora = signal(Date.now());

  readonly puedeEditar = computed(() => this.sesion.permisos().includes('reservas:editar'));

  readonly opciones = computed<OpcionFiltro<FiltroReserva>[]>(() =>
    FILTROS.map((f) => ({ ...f, etiqueta: `${f.etiqueta} (${this.enFiltro(f.valor).length})` })),
  );

  readonly visibles = computed(() => this.enFiltro(this.filtro()));

  readonly pie = computed(() => {
    const lista = this.visibles();
    const apartadas = lista.reduce((suma, r) => suma + this.apartadas(r), 0);
    const nombre = lista.length === 1 ? 'reserva' : 'reservas';
    const unidades = apartadas === 1 ? '1 unidad apartada' : `${apartadas} unidades apartadas`;
    return apartadas > 0 ? `${lista.length} ${nombre} · ${unidades} del disponible` : `${lista.length} ${nombre}`;
  });

  constructor() {
    effect(() => {
      const id = this.sucursal.id();
      untracked(() => this.cargar(id));
    });
    const reloj = setInterval(() => this.ahora.set(Date.now()), 60_000);
    inject(DestroyRef).onDestroy(() => clearInterval(reloj));
  }

  // ------------------------------------------------------------------ carga
  recargar(): void {
    this.cargar(this.sucursal.id());
  }

  private cargar(sucursalId: number | null): void {
    const pedido = ++this.pedido;
    this.errorCarga.set(null);
    if (sucursalId === null) {
      this.reservas.set([]);
      return;
    }
    this.cargando.set(true);
    this.http.get<ReservaSucursal[]>(`${API_URL}/reservas`, { params: { sucursal_id: sucursalId } }).subscribe({
      next: (filas) => {
        if (pedido !== this.pedido) return;
        this.reservas.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.errorCarga.set(mensajeDeError(err, 'No se pudieron cargar las reservas.'));
        this.cargando.set(false);
      },
    });
  }

  private enFiltro(filtro: FiltroReserva): ReservaSucursal[] {
    const todas = this.reservas();
    if (filtro === 'todas') return todas;
    if (filtro === 'activas') return todas.filter((r) => ACTIVAS.includes(r.estado));
    return todas.filter((r) => r.estado === filtro);
  }

  // --------------------------------------------------------------- acciones
  preparar(reserva: ReservaSucursal): void {
    this.ejecutar(reserva, 'preparar', (r) =>
      `Reserva #${r.id} preparada: ${r.unidades} ${r.unidades === 1 ? 'prenda lista' : 'prendas listas'} ` +
      `en el vestidor para ${r.cliente.nombre ?? 'el cliente'}.`,
    );
  }

  atender(reserva: ReservaSucursal): void {
    const apartadas = this.apartadas(reserva);
    this.ejecutar(reserva, 'atender', (r) =>
      `Reserva #${r.id} atendida: ${r.cliente.nombre ?? 'el cliente'} ya tiene las prendas. ` +
      (apartadas === 1 ? '1 unidad deja de estar apartada.' : `${apartadas} unidades dejan de estar apartadas.`),
    );
  }

  pedirExpirar(reserva: ReservaSucursal): void {
    this.errorExpirar.set(null);
    this.aExpirar.set(reserva);
  }

  confirmarExpirar(): void {
    const reserva = this.aExpirar();
    if (!reserva) return;
    const apartadas = this.apartadas(reserva);
    this.ejecutar(reserva, 'expirar', (r) =>
      apartadas === 1
        ? `Reserva #${r.id} expirada: se libero 1 unidad y ya esta disponible en ${r.sucursal}.`
        : `Reserva #${r.id} expirada: se liberaron ${apartadas} unidades y ya estan disponibles en ${r.sucursal}.`,
    );
  }

  private ejecutar(reserva: ReservaSucursal, accion: Accion, mensaje: (r: ReservaSucursal) => string): void {
    this.enProceso.set(reserva.id);
    this.http.post<ReservaSucursal>(`${API_URL}/reservas/${reserva.id}/${accion}`, {}).subscribe({
      next: (actualizada) => {
        this.enProceso.set(null);
        this.aExpirar.set(null);
        this.avisos.ok(mensaje(actualizada));
        this.recargar();
      },
      error: (err: HttpErrorResponse) => {
        this.enProceso.set(null);
        const texto = mensajeDeError(err, `No se pudo ${accion} la reserva #${reserva.id}.`);
        if (accion === 'expirar') this.errorExpirar.set(texto);
        else this.avisos.error(texto);
        // Un 400 suele ser una reserva que otra persona ya movio de estado.
        if (err.status === 400) this.recargar();
      },
    });
  }

  cerrarModal(): void {
    if (this.enProceso() === null) this.aExpirar.set(null);
  }

  // ----------------------------------------------------------- presentacion
  apartadas(reserva: ReservaSucursal): number {
    return reserva.detalle.filter((d) => d.estado === 'reservado').reduce((suma, d) => suma + d.cantidad, 0);
  }

  esActiva(reserva: ReservaSucursal): boolean {
    return ACTIVAS.includes(reserva.estado);
  }

  /** Activa y con la hora de la cita ya pasada: candidata a expirar. */
  horaPasada(reserva: ReservaSucursal): boolean {
    const cita = instanteSinZona(reserva.fecha_hora_prueba);
    return this.esActiva(reserva) && !!cita && cita.getTime() < this.ahora();
  }

  claseEstado(estado: EstadoReserva): string {
    if (estado === 'pendiente') return 'rosa';
    if (estado === 'preparada') return 'ok';
    if (estado === 'atendida') return 'neutro';
    return 'bajo';
  }

  etiquetaEstado(estado: EstadoReserva): string {
    return estado.charAt(0).toUpperCase() + estado.slice(1);
  }
}
