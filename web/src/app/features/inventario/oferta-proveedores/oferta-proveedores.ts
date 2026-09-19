import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaLocal, moneda } from '../../../shared/formato';

/** GET /api/oferta?solo_disponibles=false (backend: proveedores/service.py `_salidas`). */
interface ProductoOfrecido {
  id: number;
  proveedor_id: number;
  proveedor: string | null;
  nombre: string;
  descripcion: string | null;
  categoria_id: number | null;
  categoria: string | null;
  prenda_id: number | null;
  prenda: string | null;
  precio_referencial: number;
  cantidad_minima: number;
  disponible: boolean;
  temporadas: { id: number; nombre: string }[];
  fecha_actualizacion: string | null;
}

/** Lo que se usa de GET /api/prendas/catalogo-interno: las prendas activas de la tienda. */
interface PrendaOpcion {
  id: number;
  nombre: string;
  categoria_id: number;
  variantes: unknown[];
}

type FiltroCorrespondencia = 'todos' | 'sin' | 'con';

const FILTROS: OpcionFiltro<FiltroCorrespondencia>[] = [
  { valor: 'todos', etiqueta: 'Todos' },
  { valor: 'sin', etiqueta: 'Sin correspondencia' },
  { valor: 'con', etiqueta: 'Con correspondencia' },
];

/**
 * Oferta de los proveedores vista desde la tienda (CU9 / CU10). El proveedor
 * carga QUE vende; aca el encargado dice a que prenda del catalogo corresponde
 * cada producto. Esa correspondencia es la que, al armar una compra, acota las
 * variantes destino a las de esa prenda. El resto del producto (nombre, precio,
 * temporadas) es del proveedor y no se toca desde aca.
 */
@Component({
  selector: 'app-oferta-proveedores',
  imports: [SelectorEstado],
  templateUrl: './oferta-proveedores.html',
  styleUrl: './oferta-proveedores.css',
})
export class OfertaProveedores {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);

  readonly filtros = FILTROS;
  readonly moneda = moneda;
  readonly fecha = fechaLocal;

  readonly productos = signal<ProductoOfrecido[]>([]);
  readonly prendas = signal<PrendaOpcion[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);
  readonly guardando = signal<number | null>(null);

  readonly filtro = signal<FiltroCorrespondencia>('todos');
  readonly proveedorId = signal<number | null>(null);

  readonly puedeAsociar = computed(() => this.sesion.tienePermiso('inventario:editar'));

  readonly proveedores = computed(() => {
    const vistos = new Map<number, string>();
    this.productos().forEach((p) => vistos.set(p.proveedor_id, p.proveedor ?? `#${p.proveedor_id}`));
    return [...vistos].map(([id, nombre]) => ({ id, nombre })).sort((a, b) => a.nombre.localeCompare(b.nombre));
  });

  readonly visibles = computed(() =>
    this.productos()
      .filter((p) => this.proveedorId() === null || p.proveedor_id === this.proveedorId())
      .filter((p) => (this.filtro() === 'todos' ? true : this.filtro() === 'sin' ? p.prenda_id === null : p.prenda_id !== null)),
  );
  readonly sinCorrespondencia = computed(() => this.productos().filter((p) => p.prenda_id === null).length);

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set(null);
    forkJoin({
      productos: this.http.get<ProductoOfrecido[]>(`${API_URL}/oferta`, { params: { solo_disponibles: false } }),
      prendas: this.http.get<PrendaOpcion[]>(`${API_URL}/prendas/catalogo-interno`),
    }).subscribe({
      next: ({ productos, prendas }) => {
        this.productos.set(productos);
        this.prendas.set(prendas.sort((a, b) => a.nombre.localeCompare(b.nombre)));
        this.cargando.set(false);
      },
      error: (err) => {
        this.errorCarga.set(mensajeDeError(err, 'No se pudo cargar la oferta de los proveedores.'));
        this.cargando.set(false);
      },
    });
  }

  /** Primero las prendas de la misma categoria que declaro el proveedor: casi siempre es una de esas. */
  opcionesPara(producto: ProductoOfrecido): { sugeridas: PrendaOpcion[]; otras: PrendaOpcion[] } {
    const sugeridas = this.prendas().filter((p) => producto.categoria_id !== null && p.categoria_id === producto.categoria_id);
    return { sugeridas, otras: this.prendas().filter((p) => !sugeridas.includes(p)) };
  }

  asociar(producto: ProductoOfrecido, valor: string): void {
    const prenda_id = valor ? Number(valor) : null;
    if (prenda_id === producto.prenda_id) return;
    this.guardando.set(producto.id);
    this.http.put<ProductoOfrecido>(`${API_URL}/oferta/${producto.id}/prenda`, { prenda_id }).subscribe({
      next: (actualizado) => {
        this.guardando.set(null);
        this.productos.update((lista) => lista.map((p) => (p.id === actualizado.id ? actualizado : p)));
        this.avisos.ok(
          actualizado.prenda
            ? `«${actualizado.nombre}» corresponde a ${actualizado.prenda}: al comprarlo se ofrecen primero sus variantes.`
            : `«${actualizado.nombre}» quedo sin correspondencia.`,
        );
      },
      error: (err) => {
        this.guardando.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo guardar la correspondencia.'));
        // El <select> ya muestra lo que eligio el usuario: se vuelve a lo guardado.
        this.productos.update((lista) => [...lista]);
      },
    });
  }

  elegirProveedor(valor: string): void {
    this.proveedorId.set(valor ? Number(valor) : null);
  }
}
