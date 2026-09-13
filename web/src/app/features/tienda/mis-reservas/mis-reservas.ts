import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaLocal, fechaSinZona, instanteSinZona } from '../../../shared/formato';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';

type EstadoReserva = 'pendiente' | 'preparada' | 'atendida' | 'cancelada' | 'expirada';

/** GET /api/reservas/mias (backend: reservas/service.py `_salida`). */
interface ReservaCliente {
  id: number;
  estado: EstadoReserva;
  fecha_creacion: string | null;
  fecha_hora_prueba: string;
  notas: string | null;
  sucursal: string;
  unidades: number;
  detalle: { id: number; sku: string; prenda: string; talla: string; color: string; cantidad: number }[];
}

type Filtro = 'activas' | 'todas';

const ACTIVAS: EstadoReserva[] = ['pendiente', 'preparada'];

/** Lo que significa cada estado, contado para el cliente. */
const EXPLICACION: Record<EstadoReserva, string> = {
  pendiente: 'La sucursal recibio tu reserva y va a preparar las prendas.',
  preparada: 'Tus prendas te esperan en el vestidor.',
  atendida: 'Ya pasaste por la tienda a probartelas.',
  cancelada: 'Cancelaste esta reserva; las prendas volvieron a estar disponibles.',
  expirada: 'No llegaste a la cita y las prendas se liberaron.',
};

/** CU24: el cliente consulta sus reservas y cancela las que siguen activas. */
@Component({
  selector: 'app-mis-reservas',
  imports: [RouterLink, BarraTienda, SelectorEstado],
  templateUrl: './mis-reservas.html',
  styleUrl: './mis-reservas.css',
})
export class MisReservas {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);

  readonly fechaCita = fechaSinZona;
  readonly fechaCreada = fechaLocal;
  readonly explicacion = EXPLICACION;

  readonly reservas = signal<ReservaCliente[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);
  readonly filtro = signal<Filtro>('activas');
  readonly confirmando = signal<number | null>(null);
  readonly cancelando = signal<number | null>(null);

  readonly opciones = computed<OpcionFiltro<Filtro>[]>(() => [
    { valor: 'activas', etiqueta: `Activas (${this.reservas().filter((r) => this.activa(r)).length})` },
    { valor: 'todas', etiqueta: `Todas (${this.reservas().length})` },
  ]);

  readonly visibles = computed(() =>
    this.filtro() === 'activas' ? this.reservas().filter((r) => this.activa(r)) : this.reservas(),
  );

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<ReservaCliente[]>(`${API_URL}/reservas/mias`).subscribe({
      next: (filas) => {
        this.reservas.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar tus reservas.'));
        this.cargando.set(false);
      },
    });
  }

  activa(reserva: ReservaCliente): boolean {
    return ACTIVAS.includes(reserva.estado);
  }

  /** Sigue activa pero la hora ya paso: la sucursal la va a dar por expirada. */
  vencida(reserva: ReservaCliente): boolean {
    const cita = instanteSinZona(reserva.fecha_hora_prueba);
    return this.activa(reserva) && !!cita && cita.getTime() < Date.now();
  }

  cancelar(reserva: ReservaCliente): void {
    this.cancelando.set(reserva.id);
    this.http.post<ReservaCliente>(`${API_URL}/reservas/${reserva.id}/cancelar`, {}).subscribe({
      next: (actualizada) => {
        this.cancelando.set(null);
        this.confirmando.set(null);
        this.reservas.update((lista) => lista.map((r) => (r.id === actualizada.id ? actualizada : r)));
        this.avisos.ok(`Reserva #R-${reserva.id} cancelada. Las prendas vuelven a estar disponibles.`);
      },
      error: (err) => {
        this.cancelando.set(null);
        this.confirmando.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo cancelar la reserva.'));
        this.cargar();
      },
    });
  }
}
