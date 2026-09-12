import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { API_URL } from '../../core/api';
import { AuthService } from '../../core/auth.service';
import { mensajeDeError } from '../../core/errores.interceptor';
import { Registro, RecursoService } from '../../core/recurso.service';
import { SesionStore } from '../../core/sesion';

interface Disponibilidad {
  sucursal_id: number;
  sucursal: string;
  disponible: number;
}

interface VarianteCatalogo {
  id: number;
  sku: string;
  /** El endpoint publico devuelve los nombres ya resueltos, no los ids. */
  talla: string | null;
  color: string | null;
  imagen_url: string | null;
  disponibilidad: Disponibilidad[];
}

interface PrendaCatalogo {
  id: number;
  nombre: string;
  marca: string | null;
  precio_venta: number;
  imagen_url: string | null;
  categoria_id: number;
  coleccion_id: number | null;
  variantes: VarianteCatalogo[];
}

/** Filtros que viajan al backend como query params. */
type ClaveFiltro = 'categoria_id' | 'temporada_id' | 'talla_id' | 'color_id';

/**
 * CU16: catalogo publico. Es la unica pantalla sin guard: entra cualquiera,
 * con o sin sesion. La sucursal NO es parametro del endpoint; se aplica sobre
 * la disponibilidad que ya viene en la respuesta.
 */
@Component({
  selector: 'app-catalogo',
  imports: [RouterLink],
  templateUrl: './catalogo.html',
  styleUrl: './catalogo.css',
})
export class Catalogo {
  private http = inject(HttpClient);
  private recursos = inject(RecursoService);
  private auth = inject(AuthService);
  readonly sesion = inject(SesionStore);

  // ---- opciones de los filtros ----
  readonly temporadas = signal<Registro[]>([]);
  readonly categorias = signal<Registro[]>([]);
  readonly tallas = signal<Registro[]>([]);
  readonly colores = signal<Registro[]>([]);
  readonly sucursales = signal<Registro[]>([]);

  // ---- filtros elegidos ----
  /** Lo que se ve en la caja de busqueda; se actualiza en cada tecla. */
  readonly textoBusqueda = signal('');
  /** Lo que se consulta: el texto anterior, 350 ms despues de dejar de escribir. */
  readonly q = signal('');
  readonly categoriaId = signal<number | null>(null);
  readonly temporadaId = signal<number | null>(null);
  readonly tallaId = signal<number | null>(null);
  readonly colorId = signal<number | null>(null);
  /** Solo afecta a lo que se muestra, no a la consulta. */
  readonly sucursalId = signal<number | null>(null);

  // ---- resultados ----
  readonly prendas = signal<PrendaCatalogo[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  private temporizador?: ReturnType<typeof setTimeout>;

  readonly hayFiltros = computed(
    () =>
      this.textoBusqueda().trim() !== '' ||
      this.categoriaId() !== null ||
      this.temporadaId() !== null ||
      this.tallaId() !== null ||
      this.colorId() !== null,
  );

  readonly nombreSucursal = computed(() => {
    const id = this.sucursalId();
    if (id === null) return null;
    return String(this.sucursales().find((s) => s.id === id)?.['nombre'] ?? '');
  });

  readonly esPersonal = computed(() =>
    this.sesion.tieneAlgunRol('administrador', 'encargado', 'cajero'),
  );

  constructor() {
    this.cargarOpciones();
    // Cada cambio de filtro vuelve a consultar la API; la sucursal queda fuera
    // a proposito porque el endpoint no la recibe.
    effect(() => {
      const params = {
        q: this.q().trim(),
        categoria_id: this.categoriaId(),
        temporada_id: this.temporadaId(),
        talla_id: this.tallaId(),
        color_id: this.colorId(),
      };
      untracked(() => this.buscar(params));
    });
  }

  private cargarOpciones(): void {
    forkJoin({
      temporadas: this.recursos.listar('admin/temporadas'),
      categorias: this.recursos.listar('admin/categorias'),
      tallas: this.recursos.listar('admin/tallas'),
      colores: this.recursos.listar('admin/colores'),
      sucursales: this.recursos.listar('admin/sucursales'),
    }).subscribe({
      next: (r) => {
        this.temporadas.set(r.temporadas);
        this.categorias.set(r.categorias);
        this.tallas.set(r.tallas);
        this.colores.set(r.colores);
        this.sucursales.set(r.sucursales);
      },
      error: () => {
        // Sin opciones el catalogo sigue siendo navegable, solo sin filtros.
        this.temporadas.set([]);
      },
    });
  }

  private buscar(filtros: Record<string, string | number | null>): void {
    this.cargando.set(true);
    this.error.set(null);

    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== null && valor !== '') params = params.set(clave, String(valor));
    }

    this.http.get<PrendaCatalogo[]>(`${API_URL}/catalogo`, { params }).subscribe({
      next: (filas) => {
        this.prendas.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        this.prendas.set([]);
        this.error.set(mensajeDeError(err, 'No se pudo cargar el catalogo.'));
        this.cargando.set(false);
      },
    });
  }

  // ------------------------------------------------------------- filtros
  /** Los chips funcionan como interruptor: volver a tocarlo lo desactiva. */
  alternar(campo: ClaveFiltro, id: number): void {
    const senal = {
      categoria_id: this.categoriaId,
      temporada_id: this.temporadaId,
      talla_id: this.tallaId,
      color_id: this.colorId,
    }[campo];
    senal.set(senal() === id ? null : id);
  }

  activo(campo: ClaveFiltro, id: number): boolean {
    return {
      categoria_id: this.categoriaId(),
      temporada_id: this.temporadaId(),
      talla_id: this.tallaId(),
      color_id: this.colorId(),
    }[campo] === id;
  }

  escribir(texto: string): void {
    this.textoBusqueda.set(texto);
    clearTimeout(this.temporizador);
    this.temporizador = setTimeout(() => this.q.set(texto), 350);
  }

  /** Cerrar sesion desde el catalogo: es la unica salida que tiene un cliente. */
  salir(): void {
    this.auth.salir();
  }

  elegirSucursal(valor: string): void {
    this.sucursalId.set(valor === '' ? null : Number(valor));
  }

  limpiar(): void {
    clearTimeout(this.temporizador);
    this.textoBusqueda.set('');
    this.q.set('');
    this.categoriaId.set(null);
    this.temporadaId.set(null);
    this.tallaId.set(null);
    this.colorId.set(null);
  }

  // -------------------------------------------------------- disponibilidad
  /** Unidades libres de la prenda en la sucursal elegida (o en todas). */
  disponible(prenda: PrendaCatalogo): number {
    const id = this.sucursalId();
    return prenda.variantes.reduce((total, v) => {
      const filas = id === null ? v.disponibilidad : v.disponibilidad.filter((d) => d.sucursal_id === id);
      return total + filas.reduce((suma, d) => suma + d.disponible, 0);
    }, 0);
  }

  /** Unidades en el resto de sucursales, para el aviso de "ver otras". */
  private enOtrasSucursales(prenda: PrendaCatalogo): number {
    const id = this.sucursalId();
    if (id === null) return 0;
    return prenda.variantes.reduce(
      (total, v) =>
        total + v.disponibilidad.filter((d) => d.sucursal_id !== id).reduce((s, d) => s + d.disponible, 0),
      0,
    );
  }

  textoDisponibilidad(prenda: PrendaCatalogo): string {
    const cantidad = this.disponible(prenda);
    const sucursal = this.nombreSucursal();
    if (cantidad > 0) return sucursal ? `${cantidad} disp. en ${sucursal}` : `${cantidad} disp. en total`;
    return this.enOtrasSucursales(prenda) > 0 ? 'Agotado — hay stock en otras sucursales' : 'Agotado';
  }

  hayStock(prenda: PrendaCatalogo): boolean {
    return this.disponible(prenda) > 0;
  }

  // --------------------------------------------------------- presentacion
  hexDeColor(color: Registro): string {
    const hex = String(color['codigo_hex'] ?? '');
    return /^#[0-9a-f]{6}$/i.test(hex) ? hex : '#CCCCCC';
  }

  precio(valor: number): string {
    return Number(valor ?? 0)
      .toFixed(2)
      .replace('.', ',');
  }

  /** Tallas distintas que quedaron tras el filtro, para mostrarlas en la tarjeta. */
  tallasDe(prenda: PrendaCatalogo): string[] {
    const vistas = new Set<string>();
    for (const v of prenda.variantes) if (v.talla) vistas.add(v.talla);
    return [...vistas];
  }
}
