import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { catchError, forkJoin, of } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaLocal, moneda } from '../../../shared/formato';

/** GET /api/oferta/perfil */
interface PerfilProveedor {
  id: number;
  nombre: string;
  nit: string | null;
  contacto: string | null;
  telefono: string | null;
  email: string | null;
  productos: number;
  disponibles: number;
  ultima_actualizacion: string | null;
}

/** GET /api/oferta/mia (backend: proveedores/service.py `_salidas`). */
export interface ProductoOferta {
  id: number;
  proveedor_id: number;
  proveedor: string | null;
  nombre: string;
  descripcion: string | null;
  categoria_id: number | null;
  categoria: string | null;
  precio_referencial: number;
  cantidad_minima: number;
  disponible: boolean;
  temporada_ids: number[];
  temporadas: { id: number; nombre: string }[];
  fecha_actualizacion: string | null;
}

interface Opcion {
  id: number;
  nombre: string;
  activo?: boolean | null;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
}

type FiltroOferta = 'todos' | 'disponibles' | 'pausados';

const FILTROS: OpcionFiltro<FiltroOferta>[] = [
  { valor: 'todos', etiqueta: 'Todos' },
  { valor: 'disponibles', etiqueta: 'Disponibles' },
  { valor: 'pausados', etiqueta: 'Sin disponibilidad' },
];

const PRECIO = /^\d+([.,]\d{1,2})?$/;
const ENTERO_POSITIVO = /^[1-9]\d*$/;

/**
 * CU9 Informar productos disponibles. El proveedor mantiene la lista de lo que
 * ofrece, con precio referencial y las temporadas para las que sirve. La tienda
 * la consulta al armar una compra. Solo ve y toca SU oferta: el backend toma el
 * proveedor del token, nunca de la pantalla.
 */
@Component({
  selector: 'app-mi-oferta',
  imports: [ReactiveFormsModule, SelectorEstado],
  templateUrl: './mi-oferta.html',
  styleUrl: './mi-oferta.css',
  host: { '(document:keydown.escape)': 'cerrarModales()' },
})
export class MiOferta {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);

  readonly filtros = FILTROS;
  readonly moneda = moneda;
  readonly fecha = fechaLocal;

  readonly perfil = signal<PerfilProveedor | null>(null);
  readonly productos = signal<ProductoOferta[]>([]);
  readonly temporadas = signal<Opcion[]>([]);
  readonly categorias = signal<Opcion[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);
  /** La cuenta tiene el rol pero el administrador todavia no la enlazo a un proveedor. */
  readonly sinEnlace = signal(false);

  readonly filtro = signal<FiltroOferta>('todos');
  readonly temporadaFiltro = signal<number | null>(null);

  // ---- formulario ----
  readonly modal = signal(false);
  readonly editando = signal<ProductoOferta | null>(null);
  readonly guardando = signal(false);
  readonly intento = signal(false);
  readonly errorServidor = signal<string | null>(null);
  readonly temporadasElegidas = signal<number[]>([]);
  readonly formulario = this.fb.nonNullable.group({
    nombre: '',
    descripcion: '',
    categoria_id: '',
    precio_referencial: '',
    cantidad_minima: '1',
    disponible: true,
  });
  private readonly valores = toSignal(this.formulario.valueChanges, {
    initialValue: this.formulario.getRawValue(),
  });

  readonly aQuitar = signal<ProductoOferta | null>(null);
  readonly quitando = signal(false);
  readonly cambiando = signal<number | null>(null);

  readonly puedeCrear = computed(() => this.sesion.tienePermiso('oferta:crear'));
  readonly puedeEditar = computed(() => this.sesion.tienePermiso('oferta:editar'));
  readonly puedeEliminar = computed(() => this.sesion.tienePermiso('oferta:eliminar'));

  readonly visibles = computed(() => {
    const temporada = this.temporadaFiltro();
    return this.productos()
      .filter((p) => (this.filtro() === 'todos' ? true : this.filtro() === 'disponibles' ? p.disponible : !p.disponible))
      .filter((p) => temporada === null || p.temporada_ids.includes(temporada));
  });

  readonly errores = computed(() => {
    const v = this.valores();
    const precio = String(v.precio_referencial ?? '').trim();
    const minimo = String(v.cantidad_minima ?? '').trim();
    return {
      nombre: (v.nombre ?? '').trim() ? null : 'Como se llama el producto.',
      precio: !precio
        ? 'Falta el precio referencial.'
        : PRECIO.test(precio) && Number(precio.replace(',', '.')) > 0
          ? null
          : 'Un precio mayor que cero, con hasta 2 decimales.',
      minimo: ENTERO_POSITIVO.test(minimo) ? null : 'Un entero de 1 en adelante.',
      temporadas: this.temporadasElegidas().length > 0 ? null : 'Marca al menos una temporada.',
    };
  });
  readonly hayErrores = computed(() => Object.values(this.errores()).some((e) => e !== null));

  constructor() {
    this.cargar();
  }

  // ------------------------------------------------------------------ carga
  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set(null);
    this.sinEnlace.set(false);
    forkJoin({
      perfil: this.http.get<PerfilProveedor>(`${API_URL}/oferta/perfil`),
      productos: this.http.get<ProductoOferta[]>(`${API_URL}/oferta/mia`),
      temporadas: this.http.get<Opcion[]>(`${API_URL}/admin/temporadas`).pipe(catchError(() => of([]))),
      categorias: this.http.get<Opcion[]>(`${API_URL}/admin/categorias`).pipe(catchError(() => of([]))),
    }).subscribe({
      next: ({ perfil, productos, temporadas, categorias }) => {
        this.perfil.set(perfil);
        this.productos.set(productos);
        this.temporadas.set(temporadas.filter((t) => t.activo !== false));
        this.categorias.set(categorias.filter((c) => c.activo !== false));
        this.cargando.set(false);
      },
      error: (err: HttpErrorResponse) => {
        this.cargando.set(false);
        const mensaje = mensajeDeError(err, 'No se pudo cargar tu oferta.');
        if (err.status === 403 && /enlazada/i.test(mensaje)) this.sinEnlace.set(true);
        this.errorCarga.set(mensaje);
      },
    });
  }

  private refrescar(): void {
    forkJoin({
      perfil: this.http.get<PerfilProveedor>(`${API_URL}/oferta/perfil`),
      productos: this.http.get<ProductoOferta[]>(`${API_URL}/oferta/mia`),
    }).subscribe({
      next: ({ perfil, productos }) => {
        this.perfil.set(perfil);
        this.productos.set(productos);
      },
      error: () => {},
    });
  }

  // ------------------------------------------------------------- formulario
  abrirNuevo(): void {
    this.editando.set(null);
    // Lo habitual es ofrecer para la temporada que viene: de las que todavia no
    // terminaron, queda marcada la que empieza mas tarde.
    const hoy = new Date().toISOString().slice(0, 10);
    const proxima = this.temporadas()
      .filter((t) => t.fecha_inicio && t.fecha_fin && t.fecha_fin >= hoy)
      .sort((a, b) => (a.fecha_inicio! < b.fecha_inicio! ? 1 : -1))[0];
    this.temporadasElegidas.set(proxima ? [proxima.id] : []);
    this.formulario.reset({
      nombre: '',
      descripcion: '',
      categoria_id: '',
      precio_referencial: '',
      cantidad_minima: '1',
      disponible: true,
    });
    this.abrirModal();
  }

  abrirEdicion(producto: ProductoOferta): void {
    this.editando.set(producto);
    this.temporadasElegidas.set([...producto.temporada_ids]);
    this.formulario.reset({
      nombre: producto.nombre,
      descripcion: producto.descripcion ?? '',
      categoria_id: producto.categoria_id === null ? '' : String(producto.categoria_id),
      precio_referencial: producto.precio_referencial.toFixed(2),
      cantidad_minima: String(producto.cantidad_minima),
      disponible: producto.disponible,
    });
    this.abrirModal();
  }

  private abrirModal(): void {
    this.intento.set(false);
    this.errorServidor.set(null);
    this.modal.set(true);
  }

  alternarTemporada(id: number): void {
    this.temporadasElegidas.update((ids) => (ids.includes(id) ? ids.filter((i) => i !== id) : [...ids, id]));
  }

  guardar(): void {
    this.intento.set(true);
    if (this.hayErrores()) return;
    const crudo = this.formulario.getRawValue();
    const datos = {
      nombre: crudo.nombre.trim(),
      descripcion: crudo.descripcion.trim() || null,
      categoria_id: crudo.categoria_id ? Number(crudo.categoria_id) : null,
      precio_referencial: Number(String(crudo.precio_referencial).trim().replace(',', '.')),
      cantidad_minima: Number(crudo.cantidad_minima),
      disponible: crudo.disponible,
      temporada_ids: this.temporadasElegidas(),
    };
    const producto = this.editando();
    const peticion = producto
      ? this.http.put<ProductoOferta>(`${API_URL}/oferta/mia/${producto.id}`, datos)
      : this.http.post<ProductoOferta>(`${API_URL}/oferta/mia`, datos);

    this.guardando.set(true);
    this.errorServidor.set(null);
    peticion.subscribe({
      next: (guardado) => {
        this.guardando.set(false);
        this.modal.set(false);
        this.avisos.ok(
          producto
            ? `«${guardado.nombre}» actualizado: la tienda ya ve el precio de Bs ${moneda(guardado.precio_referencial)}.`
            : `«${guardado.nombre}» agregado a tu oferta: la tienda ya lo ve al armar sus compras.`,
        );
        this.refrescar();
      },
      error: (err) => {
        this.guardando.set(false);
        this.errorServidor.set(mensajeDeError(err, 'No se pudo guardar el producto.'));
      },
    });
  }

  // ------------------------------------------------- disponibilidad y baja
  cambiarDisponible(producto: ProductoOferta, disponible: boolean): void {
    this.cambiando.set(producto.id);
    this.http.put<ProductoOferta>(`${API_URL}/oferta/mia/${producto.id}`, { disponible }).subscribe({
      next: (p) => {
        this.cambiando.set(null);
        this.avisos.ok(
          disponible
            ? `«${p.nombre}» vuelve a estar disponible para la tienda.`
            : `«${p.nombre}» queda sin disponibilidad: la tienda deja de verlo.`,
        );
        this.refrescar();
      },
      error: (err) => {
        this.cambiando.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo cambiar la disponibilidad.'));
      },
    });
  }

  confirmarQuitar(): void {
    const producto = this.aQuitar();
    if (!producto) return;
    this.quitando.set(true);
    this.http.delete<{ detail: string }>(`${API_URL}/oferta/mia/${producto.id}`).subscribe({
      next: (r) => {
        this.quitando.set(false);
        this.aQuitar.set(null);
        this.avisos.ok(r.detail);
        this.refrescar();
      },
      error: (err) => {
        this.quitando.set(false);
        this.aQuitar.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo quitar el producto.'));
      },
    });
  }

  cerrarModales(): void {
    if (this.guardando() || this.quitando()) return;
    this.modal.set(false);
    this.aQuitar.set(null);
  }

  elegirTemporadaFiltro(valor: string): void {
    this.temporadaFiltro.set(valor ? Number(valor) : null);
  }
}
