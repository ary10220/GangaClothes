import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, forkJoin, Observable, of, switchMap, throwError } from 'rxjs';

import { API_URL } from '../../core/api';
import { mensajeDeError } from '../../core/errores.interceptor';
import { Registro, RecursoService } from '../../core/recurso.service';
import { SesionStore } from '../../core/sesion';
import { fechaSinZona, moneda, paraCampoFechaHora } from '../../shared/formato';
import { BarraTienda } from '../../shared/tienda/barra-tienda';

interface Disponibilidad {
  sucursal_id: number;
  sucursal: string;
  disponible: number;
}

interface VarianteCatalogo {
  id: number;
  sku: string;
  talla_id: number;
  talla: string;
  color_id: number;
  color: string;
  color_hex: string | null;
  imagen_url: string | null;
  /** Suma de lo disponible en las sucursales que vinieron en la respuesta. */
  disponible_total: number;
  disponibilidad: Disponibilidad[];
}

/** GET /api/catalogo (backend: prendas/service.py `armar_catalogo`). Solo prendas publicadas. */
interface PrendaCatalogo {
  id: number;
  nombre: string;
  descripcion: string | null;
  marca: string | null;
  /** Precio de lista. Con una promocion vigente (CU18) se paga `precio_final`. */
  precio_venta: number;
  precio_final: number;
  descuento: number;
  promocion: { id: number; nombre: string; etiqueta: string; fecha_fin: string | null } | null;
  imagen_url: string | null;
  categoria_id: number;
  coleccion_id: number | null;
  disponible_total: number;
  variantes: VarianteCatalogo[];
}

/** Lo que se usa del carrito (backend: ventas/service.py `salida`). */
interface CarritoResumen {
  id: number;
  sucursal_id: number;
  sucursal: string | null;
  unidades: number;
  total: number;
  detalle: { id: number }[];
}

interface Reserva {
  id: number;
  sucursal: string;
  fecha_hora_prueba: string;
}

/** Filtros que viajan al backend como query params. */
type ClaveFiltro = 'categoria_id' | 'temporada_id' | 'talla_id' | 'color_id';

const CLAVE_SUCURSAL = 'gc_sucursal_tienda';

function sucursalGuardada(): number | null {
  const id = Number(localStorage.getItem(CLAVE_SUCURSAL));
  return Number.isInteger(id) && id > 0 ? id : null;
}

/**
 * CU16/CU22 catalogo publico, con acceso a CU23 (reservar para probarse) y
 * CU17 (agregar al carrito) desde el detalle de cada prenda.
 *
 * La sucursal SI viaja al backend: con una sucursal elegida solo llegan las
 * prendas que tienen unidades ahi; sin sucursal llega todo lo publicado con
 * su disponibilidad en todas las sucursales.
 */
@Component({
  selector: 'app-catalogo',
  imports: [RouterLink, BarraTienda],
  templateUrl: './catalogo.html',
  styleUrl: './catalogo.css',
  host: { '(document:keydown.escape)': 'cerrarDetalle()' },
})
export class Catalogo {
  private http = inject(HttpClient);
  private recursos = inject(RecursoService);
  readonly sesion = inject(SesionStore);
  readonly moneda = moneda;

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
  /** Se recuerda en el navegador: es la tienda a la que suele ir el cliente. */
  readonly sucursalId = signal<number | null>(sucursalGuardada());

  // ---- resultados ----
  readonly prendas = signal<PrendaCatalogo[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  private temporizador?: ReturnType<typeof setTimeout>;
  /** Descarta respuestas viejas si se cambia un filtro antes de que lleguen. */
  private pedido = 0;

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

  readonly esCliente = computed(() => this.sesion.tieneAlgunRol('cliente'));

  // ---- detalle de una prenda ----
  readonly abierta = signal<PrendaCatalogo | null>(null);
  readonly colorSel = signal<number | null>(null);
  readonly tallaSel = signal<number | null>(null);
  readonly cantidad = signal(1);
  /** Sucursal donde se reserva o desde la que se despacha la compra. */
  readonly sucursalAccion = signal<number | null>(null);
  readonly paso = signal<'elegir' | 'reservar'>('elegir');
  readonly fechaPrueba = signal('');
  readonly notas = signal('');
  readonly enviando = signal(false);
  readonly errorAccion = signal<string | null>(null);
  readonly exito = signal<{ tipo: 'reserva' | 'carrito'; texto: string } | null>(null);
  readonly cambioSucursal = signal<{ de: string; a: string } | null>(null);
  readonly ahora = signal(paraCampoFechaHora(new Date()));

  readonly coloresDetalle = computed(() => {
    const vistos = new Map<number, { id: number; nombre: string; hex: string | null }>();
    for (const v of this.abierta()?.variantes ?? []) {
      if (!vistos.has(v.color_id)) vistos.set(v.color_id, { id: v.color_id, nombre: v.color, hex: v.color_hex });
    }
    return [...vistos.values()];
  });

  readonly tallasDetalle = computed(() => {
    const vistas = new Map<number, string>();
    for (const v of this.abierta()?.variantes ?? []) if (!vistas.has(v.talla_id)) vistas.set(v.talla_id, v.talla);
    return [...vistas].map(([id, nombre]) => ({ id, nombre }));
  });

  readonly variante = computed(
    () => this.abierta()?.variantes.find((v) => v.talla_id === this.tallaSel() && v.color_id === this.colorSel()) ?? null,
  );

  readonly sucursalesConStock = computed(() => (this.variante()?.disponibilidad ?? []).filter((d) => d.disponible > 0));

  readonly disponibleAccion = computed(() => {
    const id = this.sucursalAccion();
    return this.variante()?.disponibilidad.find((d) => d.sucursal_id === id)?.disponible ?? 0;
  });

  readonly nombreSucursalAccion = computed(
    () => this.sucursalesConStock().find((d) => d.sucursal_id === this.sucursalAccion())?.sucursal ?? '',
  );

  readonly bloqueo = computed<string | null>(() => {
    if (!this.variante()) return 'Elige una talla y un color.';
    if (this.sucursalesConStock().length === 0) {
      const donde = this.nombreSucursal();
      return donde ? `Esta talla y color estan agotados en ${donde}.` : 'Esta talla y color estan agotados.';
    }
    if (this.sucursalAccion() === null) return 'Elige la sucursal.';
    const cantidad = this.cantidad();
    if (!Number.isInteger(cantidad) || cantidad < 1) return 'La cantidad minima es 1.';
    if (cantidad > this.disponibleAccion()) {
      return `Solo hay ${this.disponibleAccion()} disponibles en ${this.nombreSucursalAccion()}.`;
    }
    return null;
  });

  constructor() {
    this.cargarOpciones();
    // Cada cambio de filtro, sucursal incluida, vuelve a consultar la API.
    effect(() => {
      const params = {
        q: this.q().trim(),
        categoria_id: this.categoriaId(),
        temporada_id: this.temporadaId(),
        talla_id: this.tallaId(),
        color_id: this.colorId(),
        sucursal_id: this.sucursalId(),
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
        const activas = r.sucursales.filter((s) => s['activo'] !== false);
        this.temporadas.set(r.temporadas.filter((t) => t['activo'] !== false));
        this.categorias.set(r.categorias.filter((c) => c['activo'] !== false));
        this.tallas.set(r.tallas);
        this.colores.set(r.colores);
        this.sucursales.set(activas);
        // La sucursal recordada pudo desactivarse: se vuelve a "todas".
        const id = this.sucursalId();
        if (id !== null && !activas.some((s) => s.id === id)) this.elegirSucursal('');
      },
      error: () => {
        // Sin opciones el catalogo sigue siendo navegable, solo sin filtros.
        this.temporadas.set([]);
      },
    });
  }

  private buscar(filtros: Record<string, string | number | null>): void {
    const pedido = ++this.pedido;
    this.cargando.set(true);
    this.error.set(null);

    let params = new HttpParams();
    for (const [clave, valor] of Object.entries(filtros)) {
      if (valor !== null && valor !== '') params = params.set(clave, String(valor));
    }

    this.http.get<PrendaCatalogo[]>(`${API_URL}/catalogo`, { params }).subscribe({
      next: (filas) => {
        if (pedido !== this.pedido) return;
        this.prendas.set(filas);
        this.cargando.set(false);
        // El detalle abierto se refresca con la disponibilidad nueva.
        const abierta = this.abierta();
        const nueva = abierta && filas.find((p) => p.id === abierta.id);
        if (nueva) this.abierta.set(nueva);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.prendas.set([]);
        this.error.set(mensajeDeError(err, 'No se pudo cargar el catalogo.'));
        this.cargando.set(false);
      },
    });
  }

  /** Despues de reservar: la disponibilidad cambio, se vuelve a pedir con los mismos filtros. */
  private recargar(): void {
    this.buscar({
      q: this.q(),
      categoria_id: this.categoriaId(),
      temporada_id: this.temporadaId(),
      talla_id: this.tallaId(),
      color_id: this.colorId(),
      sucursal_id: this.sucursalId(),
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
    return (
      {
        categoria_id: this.categoriaId(),
        temporada_id: this.temporadaId(),
        talla_id: this.tallaId(),
        color_id: this.colorId(),
      }[campo] === id
    );
  }

  escribir(texto: string): void {
    this.textoBusqueda.set(texto);
    clearTimeout(this.temporizador);
    this.temporizador = setTimeout(() => this.q.set(texto), 350);
  }

  elegirSucursal(valor: string): void {
    const id = valor === '' ? null : Number(valor);
    this.sucursalId.set(id);
    if (id === null) localStorage.removeItem(CLAVE_SUCURSAL);
    else localStorage.setItem(CLAVE_SUCURSAL, String(id));
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

  // ------------------------------------------------------ tarjeta del listado
  textoDisponibilidad(prenda: PrendaCatalogo): string {
    const cantidad = prenda.disponible_total;
    const sucursal = this.nombreSucursal();
    if (sucursal) return `${cantidad} disponibles en ${sucursal}`;
    if (cantidad <= 0) return 'Agotado por ahora';
    const tiendas = new Set(
      prenda.variantes.flatMap((v) => v.disponibilidad.filter((d) => d.disponible > 0).map((d) => d.sucursal_id)),
    ).size;
    return `${cantidad} disponibles en ${tiendas} ${tiendas === 1 ? 'sucursal' : 'sucursales'}`;
  }

  /** Tallas distintas que quedaron tras el filtro, para mostrarlas en la tarjeta. */
  tallasDe(prenda: PrendaCatalogo): string[] {
    return [...new Set(prenda.variantes.map((v) => v.talla))];
  }

  hexDeColor(color: Registro): string {
    return this.hex(String(color['codigo_hex'] ?? ''));
  }

  hex(valor: string | null): string {
    return /^#[0-9a-f]{6}$/i.test(valor ?? '') ? valor! : '#CCCCCC';
  }

  // ---------------------------------------------------------------- detalle
  abrir(prenda: PrendaCatalogo): void {
    this.abierta.set(prenda);
    this.paso.set('elegir');
    this.cantidad.set(1);
    this.notas.set('');
    this.fechaPrueba.set('');
    this.errorAccion.set(null);
    this.exito.set(null);
    this.cambioSucursal.set(null);
    // Arranca en la primera combinacion que se puede llevar.
    const inicial = prenda.variantes.find((v) => v.disponible_total > 0) ?? prenda.variantes[0];
    this.colorSel.set(inicial?.color_id ?? null);
    this.tallaSel.set(inicial?.talla_id ?? null);
    this.ajustarSucursal();
  }

  cerrarDetalle(): void {
    this.abierta.set(null);
  }

  elegirColor(id: number): void {
    this.colorSel.set(id);
    if (!this.variante()) {
      const delColor = this.abierta()!.variantes.filter((v) => v.color_id === id);
      const conStock = delColor.find((v) => v.disponible_total > 0) ?? delColor[0];
      this.tallaSel.set(conStock?.talla_id ?? null);
    }
    this.ajustarSucursal();
  }

  elegirTalla(id: number): void {
    this.tallaSel.set(id);
    this.ajustarSucursal();
  }

  /** La talla no existe en ese color o no tiene unidades. */
  tallaAgotada(tallaId: number): boolean {
    const v = this.abierta()?.variantes.find((x) => x.talla_id === tallaId && x.color_id === this.colorSel());
    return !v || v.disponible_total <= 0;
  }

  private ajustarSucursal(): void {
    this.errorAccion.set(null);
    this.exito.set(null);
    this.cambioSucursal.set(null);
    const opciones = this.sucursalesConStock();
    const elegida = this.sucursalId() ?? this.sucursalAccion();
    const sigue = opciones.some((d) => d.sucursal_id === elegida);
    this.sucursalAccion.set(sigue ? elegida : (opciones[0]?.sucursal_id ?? null));
    if (this.cantidad() > this.disponibleAccion()) this.cantidad.set(Math.max(1, this.disponibleAccion()));
  }

  elegirSucursalAccion(valor: string): void {
    this.sucursalAccion.set(Number(valor));
    this.errorAccion.set(null);
    this.cambioSucursal.set(null);
  }

  cambiarCantidad(valor: string | number): void {
    this.cantidad.set(Math.trunc(Number(valor)) || 0);
    this.errorAccion.set(null);
  }

  // ------------------------------------------------------------ CU23 reservar
  irAReservar(): void {
    if (this.bloqueo()) return;
    this.ahora.set(paraCampoFechaHora(new Date()));
    if (!this.fechaPrueba()) {
      const manana = new Date();
      manana.setDate(manana.getDate() + 1);
      manana.setHours(10, 0, 0, 0);
      this.fechaPrueba.set(paraCampoFechaHora(manana));
    }
    this.errorAccion.set(null);
    this.paso.set('reservar');
  }

  reservar(): void {
    const variante = this.variante();
    if (!variante || this.bloqueo()) return;
    const fecha = this.fechaPrueba();
    if (!fecha || new Date(fecha).getTime() <= Date.now()) {
      this.errorAccion.set('Elige una fecha y hora futuras para tu visita.');
      return;
    }

    this.enviando.set(true);
    this.errorAccion.set(null);
    const datos = {
      sucursal_id: this.sucursalAccion(),
      // La hora viaja tal cual la eligio el cliente, sin zona: es hora de la tienda.
      fecha_hora_prueba: `${fecha}:00`,
      notas: this.notas().trim() || null,
      detalle: [{ variante_id: variante.id, cantidad: this.cantidad() }],
    };
    this.http.post<Reserva>(`${API_URL}/reservas`, datos).subscribe({
      next: (reserva) => {
        this.enviando.set(false);
        this.paso.set('elegir');
        this.exito.set({
          tipo: 'reserva',
          texto: `Reserva #R-${reserva.id} confirmada en ${reserva.sucursal} para el ${fechaSinZona(reserva.fecha_hora_prueba)}.`,
        });
        this.recargar();
      },
      error: (err) => {
        this.enviando.set(false);
        this.errorAccion.set(mensajeDeError(err, 'No se pudo crear la reserva.'));
        if (err.status === 400) this.recargar();
      },
    });
  }

  // ------------------------------------------------------------- CU17 carrito
  agregarAlCarrito(confirmarCambio = false): void {
    const variante = this.variante();
    const sucursalId = this.sucursalAccion();
    if (!variante || sucursalId === null || this.bloqueo()) return;

    this.enviando.set(true);
    this.errorAccion.set(null);
    const actual: Observable<CarritoResumen | null> = this.http
      .get<CarritoResumen>(`${API_URL}/ventas/carrito`)
      .pipe(catchError((err: HttpErrorResponse) => (err.status === 404 ? of(null) : throwError(() => err))));

    actual
      .pipe(
        switchMap((carrito) => {
          // Un carrito se despacha desde una sola sucursal: cambiarla afecta a lo que ya tiene.
          if (carrito && carrito.sucursal_id !== sucursalId && carrito.detalle.length > 0 && !confirmarCambio) {
            this.cambioSucursal.set({ de: carrito.sucursal ?? '', a: this.nombreSucursalAccion() });
            return of(null);
          }
          const abrir =
            carrito && carrito.sucursal_id === sucursalId
              ? of(carrito)
              : this.http.post<CarritoResumen>(`${API_URL}/ventas/carrito`, { sucursal_id: sucursalId });
          return abrir.pipe(
            switchMap(() =>
              this.http.post<CarritoResumen>(`${API_URL}/ventas/carrito/items`, {
                variante_id: variante.id,
                cantidad: this.cantidad(),
              }),
            ),
          );
        }),
      )
      .subscribe({
        next: (carrito) => {
          this.enviando.set(false);
          if (!carrito) return;
          this.cambioSucursal.set(null);
          this.exito.set({
            tipo: 'carrito',
            texto: `Agregado al carrito. Llevas ${carrito.unidades} ${carrito.unidades === 1 ? 'prenda' : 'prendas'} por Bs ${moneda(carrito.total)}, desde ${carrito.sucursal}.`,
          });
        },
        error: (err) => {
          this.enviando.set(false);
          this.errorAccion.set(mensajeDeError(err, 'No se pudo agregar al carrito.'));
        },
      });
  }
}
