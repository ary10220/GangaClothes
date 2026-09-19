import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { SucursalActual } from '../../../core/sucursal-actual';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { fechaLocal, moneda } from '../../../shared/formato';
import { SelectorSucursal } from '../../../shared/sucursal/selector-sucursal';

type EstadoCompra = 'pendiente' | 'recibida' | 'anulada';
type FiltroCompra = 'pendiente' | 'recibida' | 'todas';

/** GET /api/compras y /api/compras/{id} (backend: inventario/service.py `_fila_compra`). */
interface Compra {
  id: number;
  fecha: string | null;
  estado: EstadoCompra;
  total: number;
  proveedor_id: number;
  proveedor: string | null;
  sucursal_id: number;
  sucursal: string | null;
  items: number;
  detalle?: LineaCompra[];
}

interface LineaCompra {
  id: number;
  /** Producto de la oferta del proveedor del que partio la linea (null: compra sin oferta). */
  producto_proveedor: string | null;
  variante_id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

interface ResultadoRecepcion {
  compra: Compra;
  movimientos: { cantidad: number }[];
}

interface Proveedor {
  id: number;
  nombre: string;
  activo: boolean | null;
}

/**
 * Lo que se usa de GET /api/prendas/catalogo-interno: prendas activas (publicadas
 * o no) con sus variantes y stock por sucursal. Se compra antes de publicar.
 */
interface PrendaCatalogo {
  id: number;
  nombre: string;
  variantes: {
    id: number;
    sku: string;
    talla: string | null;
    color: string | null;
    disponibilidad: { sucursal_id: number; disponible: number }[];
  }[];
}

/** GET /api/oferta?proveedor_id= : lo que el proveedor informo en su portal (CU9). */
interface ProductoOfrecido {
  id: number;
  nombre: string;
  descripcion: string | null;
  categoria: string | null;
  precio_referencial: number;
  cantidad_minima: number;
  temporadas: { id: number; nombre: string }[];
  fecha_actualizacion: string | null;
  /** Prenda del catalogo a la que corresponde (la define la tienda en «Oferta de proveedores»). */
  prenda_id: number | null;
  prenda: string | null;
}

interface OpcionVariante {
  id: number;
  prenda_id: number;
  prenda: string;
  sku: string;
  talla: string;
  color: string;
  costo: number | null;
  disponibilidad: { sucursal_id: number; disponible: number }[];
}

interface GrupoVariantes {
  prenda_id: number;
  prenda: string;
  /** Es la prenda a la que corresponde el producto elegido en la linea. */
  asociada?: boolean;
  variantes: OpcionVariante[];
}

type LineaForm = FormGroup<{
  /** Producto de la oferta del proveedor: de ahi parte la linea. Vacio si no hay oferta. */
  producto_id: FormControl<string>;
  variante_id: FormControl<string>;
  cantidad: FormControl<string>;
  precio_unitario: FormControl<string>;
}>;

interface ErroresLinea {
  producto: string | null;
  variante: string | null;
  cantidad: string | null;
  precio: string | null;
}

const FILTROS: OpcionFiltro<FiltroCompra>[] = [
  { valor: 'pendiente', etiqueta: 'Pendientes' },
  { valor: 'recibida', etiqueta: 'Recibidas' },
  { valor: 'todas', etiqueta: 'Todas' },
];

const ENTERO_POSITIVO = /^[1-9]\d*$/;
const PRECIO = /^\d+([.,]\d{1,2})?$/;

/** Los inputs numericos entregan number; el formulario se trabaja como texto. */
const texto = (valor: unknown) => String(valor ?? '').trim();
const precioDe = (valor: unknown) => (PRECIO.test(texto(valor)) ? Number(texto(valor).replace(',', '.')) : null);

/**
 * CU10: compras a proveedor de la sucursal. Una compra nace pendiente; al
 * recibirla el backend suma el stock de cada linea y deja su movimiento.
 *
 * La compra parte de lo que el proveedor ofrece (CU9): cada linea es
 * producto del proveedor -> variante destino del catalogo -> cantidad. Solo si
 * el proveedor no cargo oferta se arma libremente, y la pantalla lo avisa.
 */
@Component({
  selector: 'app-compras',
  imports: [ReactiveFormsModule, SelectorEstado, SelectorSucursal],
  templateUrl: './compras.html',
  styleUrl: './compras.css',
  host: { '(document:keydown.escape)': 'cerrarModales()' },
})
export class Compras {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);
  private router = inject(Router);
  private ruta = inject(ActivatedRoute);
  readonly sucursal = inject(SucursalActual);

  /** `?nueva=1&variante=ID` abre el formulario (botones "Compra a proveedor" y "Reponer" del inventario). */
  readonly nueva = input<string>();
  readonly variante = input<string>();

  readonly filtros = FILTROS;
  readonly moneda = moneda;
  readonly fecha = fechaLocal;

  // ---- listado ----
  readonly compras = signal<Compra[]>([]);
  readonly cargando = signal(false);
  readonly errorCarga = signal<string | null>(null);
  readonly filtro = signal<FiltroCompra>('pendiente');
  private pedido = 0;

  // ---- datos para armar una compra ----
  readonly proveedores = signal<Proveedor[]>([]);
  readonly grupos = signal<GrupoVariantes[]>([]);
  readonly cargandoCatalogo = signal(false);
  readonly errorCatalogo = signal<string | null>(null);
  private catalogoCargado = false;

  // ---- detalle y recepcion ----
  readonly abierta = signal<Compra | null>(null);
  readonly cargandoDetalle = signal<number | null>(null);
  readonly aRecibir = signal<Compra | null>(null);
  readonly recibiendo = signal(false);
  readonly errorRecibir = signal<string | null>(null);

  // ---- nueva compra ----
  readonly modalNueva = signal(false);
  readonly guardando = signal(false);
  readonly intento = signal(false);
  readonly errorServidor = signal<string | null>(null);
  readonly formCompra = this.fb.nonNullable.group({
    proveedor_id: '',
    sucursal_id: '',
    lineas: this.fb.array<LineaForm>([]),
  });
  private readonly valores = toSignal(this.formCompra.valueChanges, {
    initialValue: this.formCompra.getRawValue(),
  });
  // ---- oferta del proveedor elegido (CU9) ----
  readonly oferta = signal<ProductoOfrecido[]>([]);
  readonly cargandoOferta = signal(false);
  readonly errorOferta = signal<string | null>(null);
  readonly temporadaOferta = signal<number | null>(null);
  private pedidoOferta = 0;

  private readonly proveedorIdElegido = computed(() => Number(this.valores().proveedor_id) || null);
  readonly proveedorElegido = computed(
    () => this.proveedores().find((p) => p.id === this.proveedorIdElegido()) ?? null,
  );
  readonly temporadasOferta = computed(() => {
    const vistas = new Map<number, string>();
    this.oferta().forEach((p) => p.temporadas.forEach((t) => vistas.set(t.id, t.nombre)));
    return [...vistas].map(([id, nombre]) => ({ id, nombre })).sort((a, b) => a.nombre.localeCompare(b.nombre));
  });
  readonly ofertaVisible = computed(() => {
    const temporada = this.temporadaOferta();
    return temporada === null
      ? this.oferta()
      : this.oferta().filter((p) => p.temporadas.some((t) => t.id === temporada));
  });
  private readonly productosPorId = computed(() => new Map(this.oferta().map((p) => [p.id, p] as const)));
  /** El proveedor elegido cargo productos: las lineas tienen que partir de ellos. */
  readonly hayOferta = computed(() => this.oferta().length > 0);
  readonly sinOferta = computed(
    () => this.proveedorElegido() !== null && !this.cargandoOferta() && !this.errorOferta() && !this.hayOferta(),
  );
  readonly asociando = signal<number | null>(null);

  /** Precio que puso la pantalla en cada linea: mientras nadie lo cambie, sigue a la variante elegida. */
  private readonly sugeridos = new WeakMap<LineaForm, string>();

  readonly puedeCrear = computed(() => this.sesion.permisos().includes('inventario:crear'));
  readonly puedeRecibir = computed(() => this.sesion.permisos().includes('inventario:editar'));

  readonly visibles = computed(() =>
    this.filtro() === 'todas' ? this.compras() : this.compras().filter((c) => c.estado === this.filtro()),
  );
  readonly pendientes = computed(() => this.compras().filter((c) => c.estado === 'pendiente').length);
  readonly pie = computed(() => {
    const lista = this.visibles();
    const monto = lista.reduce((suma, c) => suma + Number(c.total || 0), 0);
    return `${lista.length} ${lista.length === 1 ? 'compra' : 'compras'} · Bs ${moneda(monto)}`;
  });

  private readonly variantesPorId = computed(
    () => new Map(this.grupos().flatMap((g) => g.variantes.map((v) => [v.id, v] as const))),
  );

  readonly erroresLinea = computed(() => this.revisarLineas(this.intento()));
  readonly errorProveedor = computed(() =>
    this.intento() && !texto(this.valores().proveedor_id) ? 'Elegi el proveedor.' : null,
  );
  readonly errorSinLineas = computed(() =>
    this.intento() && (this.valores().lineas ?? []).length === 0 ? 'Agrega al menos una linea.' : null,
  );
  readonly total = computed(() =>
    (this.valores().lineas ?? []).reduce((suma, _l, i) => suma + this.subtotalLinea(i), 0),
  );

  get lineas(): FormArray<LineaForm> {
    return this.formCompra.controls.lineas;
  }

  constructor() {
    effect(() => {
      const id = this.sucursal.id();
      untracked(() => this.cargar(id));
    });
    effect(() => {
      if (this.nueva() && this.puedeCrear()) {
        const variante = Number(this.variante());
        untracked(() => {
          this.abrirNueva(Number.isInteger(variante) && variante > 0 ? variante : null);
          this.limpiarParametros();
        });
      }
    });
    effect(() => {
      this.valores();
      untracked(() => this.errorServidor.set(null));
    });
    effect(() => {
      // Depende del id y no del formulario entero: al llegar la oferta se tocan las
      // lineas, y eso no tiene que volver a pedirla.
      const proveedorId = this.proveedorIdElegido();
      const abierto = this.modalNueva();
      untracked(() => this.cargarOferta(abierto ? proveedorId : null));
    });
  }

  /** Lo que ese proveedor informo que puede vender: se consulta, no se edita. */
  private cargarOferta(proveedorId: number | null): void {
    const pedido = ++this.pedidoOferta;
    this.oferta.set([]);
    this.errorOferta.set(null);
    this.temporadaOferta.set(null);
    if (proveedorId === null) {
      this.cargandoOferta.set(false);
      return;
    }
    this.cargandoOferta.set(true);
    this.http.get<ProductoOfrecido[]>(`${API_URL}/oferta`, { params: { proveedor_id: proveedorId } }).subscribe({
      next: (productos) => {
        if (pedido !== this.pedidoOferta) return;
        this.oferta.set(productos);
        this.cargandoOferta.set(false);
        this.alCambiarOferta();
      },
      error: (err) => {
        if (pedido !== this.pedidoOferta) return;
        this.errorOferta.set(mensajeDeError(err, 'No se pudo consultar la oferta del proveedor.'));
        this.cargandoOferta.set(false);
      },
    });
  }

  elegirTemporadaOferta(valor: string): void {
    this.temporadaOferta.set(valor ? Number(valor) : null);
  }

  /**
   * Cambio el proveedor: los productos elegidos eran del anterior. Si una linea ya
   * traia su variante (boton «Reponer» del inventario) y un solo producto de la
   * oferta nueva corresponde a esa prenda, queda elegido.
   */
  private alCambiarOferta(): void {
    this.lineas.controls.forEach((linea, i) => {
      const variante = this.variantesPorId().get(Number(linea.controls.variante_id.value));
      const candidatos = variante ? this.oferta().filter((p) => p.prenda_id === variante.prenda_id) : [];
      linea.controls.producto_id.setValue(candidatos.length === 1 ? String(candidatos[0].id) : '');
      this.sugerirPrecio(i);
    });
  }

  producto(indice: number): ProductoOfrecido | null {
    const linea = (this.valores().lineas ?? [])[indice];
    return this.productosPorId().get(Number(linea?.producto_id)) ?? null;
  }

  /** Productos que se ofrecen en el selector de la linea: los de la temporada filtrada, mas el ya elegido. */
  productosPara(indice: number): ProductoOfrecido[] {
    const elegido = this.producto(indice);
    const visibles = this.ofertaVisible();
    return elegido && !visibles.includes(elegido) ? [elegido, ...visibles] : visibles;
  }

  /** Variantes destino: primero las de la prenda a la que corresponde el producto elegido. */
  gruposPara(indice: number): GrupoVariantes[] {
    const prendaId = this.producto(indice)?.prenda_id ?? null;
    if (prendaId === null) return this.grupos();
    const asociada = this.grupos().find((g) => g.prenda_id === prendaId);
    if (!asociada) return this.grupos();
    return [{ ...asociada, asociada: true }, ...this.grupos().filter((g) => g !== asociada)];
  }

  alElegirProducto(indice: number): void {
    const linea = this.lineas.at(indice);
    const producto = this.productosPorId().get(Number(linea.controls.producto_id.value));
    const variante = this.variantesPorId().get(Number(linea.controls.variante_id.value));
    // La variante que habia era de otra prenda: se vuelve a elegir entre las que corresponden.
    if (producto?.prenda_id && variante && variante.prenda_id !== producto.prenda_id) {
      linea.controls.variante_id.setValue('');
    }
    this.sugerirPrecio(indice);
  }

  /** Avisos de la linea que no impiden guardar. */
  avisosLinea(indice: number): string[] {
    const producto = this.producto(indice);
    if (!producto) return [];
    const linea = (this.valores().lineas ?? [])[indice];
    const variante = this.variantesPorId().get(Number(linea?.variante_id));
    const avisos: string[] = [];
    if (producto.prenda_id === null) {
      avisos.push(
        `«${producto.nombre}» no tiene correspondencia definida todavia con una prenda del catalogo: ` +
          'podes elegir cualquier variante.',
      );
    } else if (variante && variante.prenda_id !== producto.prenda_id) {
      avisos.push(`«${producto.nombre}» corresponde a ${producto.prenda}, y elegiste una variante de ${variante.prenda}.`);
    }
    const pedidas = (this.valores().lineas ?? [])
      .filter((l) => Number(l.producto_id) === producto.id && ENTERO_POSITIVO.test(texto(l.cantidad)))
      .reduce((suma, l) => suma + Number(texto(l.cantidad)), 0);
    if (pedidas > 0 && pedidas < producto.cantidad_minima) {
      avisos.push(`El pedido minimo de «${producto.nombre}» es de ${producto.cantidad_minima} unidades y llevas ${pedidas}.`);
    }
    return avisos;
  }

  /** Se puede dejar definida la correspondencia desde aca: producto sin prenda + variante ya elegida. */
  prendaParaAsociar(indice: number): { productoId: number; prendaId: number; prenda: string } | null {
    const producto = this.producto(indice);
    const linea = (this.valores().lineas ?? [])[indice];
    const variante = this.variantesPorId().get(Number(linea?.variante_id));
    if (!producto || producto.prenda_id !== null || !variante || !this.puedeRecibir()) return null;
    return { productoId: producto.id, prendaId: variante.prenda_id, prenda: variante.prenda };
  }

  asociar(indice: number): void {
    const destino = this.prendaParaAsociar(indice);
    if (!destino) return;
    this.asociando.set(destino.productoId);
    this.http
      .put<ProductoOfrecido>(`${API_URL}/oferta/${destino.productoId}/prenda`, { prenda_id: destino.prendaId })
      .subscribe({
        next: (actualizado) => {
          this.asociando.set(null);
          this.oferta.update((lista) => lista.map((p) => (p.id === actualizado.id ? { ...p, ...actualizado } : p)));
          this.avisos.ok(`«${actualizado.nombre}» queda asociado a ${actualizado.prenda}: la proxima vez se ofrecen primero sus variantes.`);
        },
        error: (err) => {
          this.asociando.set(null);
          this.avisos.error(mensajeDeError(err, 'No se pudo guardar la correspondencia.'));
        },
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
      this.compras.set([]);
      return;
    }
    this.cargando.set(true);
    this.http.get<Compra[]>(`${API_URL}/compras`, { params: { sucursal_id: sucursalId } }).subscribe({
      next: (filas) => {
        if (pedido !== this.pedido) return;
        this.compras.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        if (pedido !== this.pedido) return;
        this.errorCarga.set(mensajeDeError(err, 'No se pudieron cargar las compras.'));
        this.cargando.set(false);
      },
    });
  }

  private cargarCatalogo(): void {
    if (this.catalogoCargado || this.cargandoCatalogo()) return;
    this.cargandoCatalogo.set(true);
    this.errorCatalogo.set(null);
    forkJoin({
      proveedores: this.http.get<Proveedor[]>(`${API_URL}/admin/proveedores`),
      catalogo: this.http.get<PrendaCatalogo[]>(`${API_URL}/prendas/catalogo-interno`),
      // El costo solo sirve para sugerir el precio: si no hay permiso, se sigue sin el.
      prendas: this.http
        .get<{ id: number; costo: number | string }[]>(`${API_URL}/prendas`)
        .pipe(catchError(() => of([]))),
    }).subscribe({
      next: ({ proveedores, catalogo, prendas }) => {
        const costos = new Map(prendas.map((p) => [p.id, Number(p.costo)]));
        this.proveedores.set(
          proveedores.filter((p) => p.activo !== false).sort((a, b) => a.nombre.localeCompare(b.nombre)),
        );
        this.grupos.set(
          catalogo
            .filter((p) => p.variantes.length > 0)
            .sort((a, b) => a.nombre.localeCompare(b.nombre))
            .map((p) => ({
              prenda_id: p.id,
              prenda: p.nombre,
              variantes: p.variantes.map((v) => ({
                id: v.id,
                prenda_id: p.id,
                prenda: p.nombre,
                sku: v.sku,
                talla: v.talla ?? '—',
                color: v.color ?? '—',
                costo: costos.get(p.id) ?? null,
                disponibilidad: v.disponibilidad,
              })),
            })),
        );
        this.catalogoCargado = true;
        this.cargandoCatalogo.set(false);
        this.completarPrecios();
      },
      error: (err) => {
        this.errorCatalogo.set(mensajeDeError(err, 'No se pudieron cargar proveedores y prendas.'));
        this.cargandoCatalogo.set(false);
      },
    });
  }

  // ---------------------------------------------------------- nueva compra
  abrirNueva(varianteId: number | null = null): void {
    this.cargarCatalogo();
    this.intento.set(false);
    this.lineas.clear();
    this.formCompra.reset({ proveedor_id: '', sucursal_id: String(this.sucursal.id() ?? '') });
    this.agregarLinea(varianteId);
    this.errorServidor.set(null);
    this.modalNueva.set(true);
  }

  agregarLinea(varianteId: number | null = null): void {
    const linea = this.fb.nonNullable.group({
      producto_id: '',
      variante_id: varianteId === null ? '' : String(varianteId),
      cantidad: '',
      precio_unitario: '',
    });
    this.lineas.push(linea);
    this.alElegirVariante(this.lineas.length - 1);
  }

  quitarLinea(indice: number): void {
    this.lineas.removeAt(indice);
  }

  alElegirVariante(indice: number): void {
    this.sugerirPrecio(indice);
  }

  /**
   * Sugiere el precio referencial del producto del proveedor; sin oferta, el costo
   * de la prenda. Nunca pisa un precio que el usuario ya escribio a mano.
   */
  private sugerirPrecio(indice: number): void {
    const linea = this.lineas.at(indice);
    const producto = this.productosPorId().get(Number(linea.controls.producto_id.value));
    const base = producto
      ? producto.precio_referencial
      : this.hayOferta()
        ? null
        : this.variantesPorId().get(Number(linea.controls.variante_id.value))?.costo;
    const actual = texto(linea.controls.precio_unitario.value);
    if (base == null || (actual !== '' && actual !== this.sugeridos.get(linea))) return;
    const sugerido = base.toFixed(2);
    linea.controls.precio_unitario.setValue(sugerido);
    this.sugeridos.set(linea, sugerido);
  }

  /** Quita `?nueva` de la URL: si quedara, recargar la pagina volveria a abrir el formulario. */
  private limpiarParametros(): void {
    this.router.navigate([], {
      relativeTo: this.ruta,
      queryParams: { nueva: null, variante: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  /** Si el formulario se abrio antes de que llegara el catalogo, completa los precios vacios. */
  private completarPrecios(): void {
    this.lineas.controls.forEach((_linea, i) => this.alElegirVariante(i));
  }

  private revisarLineas(mostrarFaltantes: boolean): ErroresLinea[] {
    const lineas = this.valores().lineas ?? [];
    return lineas.map((linea, i) => {
      const variante = texto(linea.variante_id);
      const cantidad = texto(linea.cantidad);
      const precio = texto(linea.precio_unitario);
      const primera = lineas.findIndex((otra) => texto(otra.variante_id) === variante);
      return {
        producto:
          this.hayOferta() && !texto(linea.producto_id) && mostrarFaltantes
            ? 'Elegi el producto del proveedor.'
            : null,
        variante: !variante
          ? mostrarFaltantes
            ? 'Elegi la variante.'
            : null
          : primera < i
            ? `Esta variante ya esta en la linea ${primera + 1}.`
            : null,
        cantidad: !cantidad
          ? mostrarFaltantes
            ? 'Falta la cantidad.'
            : null
          : ENTERO_POSITIVO.test(cantidad)
            ? null
            : 'La cantidad es un entero mayor que cero.',
        precio: !precio
          ? mostrarFaltantes
            ? 'Falta el precio unitario.'
            : null
          : PRECIO.test(precio)
            ? null
            : 'El precio va con hasta 2 decimales.',
      };
    });
  }

  /** Los errores de una linea en una sola frase, o cadena vacia si esta bien. */
  mensajesLinea(indice: number): string {
    const errores = this.erroresLinea()[indice];
    return errores
      ? [errores.producto, errores.variante, errores.cantidad, errores.precio].filter((m) => m !== null).join(' ')
      : '';
  }

  subtotalLinea(indice: number): number {
    const linea = (this.valores().lineas ?? [])[indice];
    if (!linea || !ENTERO_POSITIVO.test(texto(linea.cantidad))) return 0;
    const precio = precioDe(linea.precio_unitario);
    return precio === null ? 0 : Math.round(Number(texto(linea.cantidad)) * precio * 100) / 100;
  }

  stockTexto(indice: number): string {
    const linea = (this.valores().lineas ?? [])[indice];
    const variante = this.variantesPorId().get(Number(linea?.variante_id));
    if (!variante) return '';
    const sucursalId = Number(this.valores().sucursal_id);
    const stock = variante.disponibilidad.find((d) => d.sucursal_id === sucursalId);
    const partes = [stock ? `${stock.disponible} disponibles en la sucursal` : 'sin stock en la sucursal: se abre al recibir'];
    if (variante.costo !== null) partes.push(`costo actual Bs ${moneda(variante.costo)}`);
    return partes.join(' · ');
  }

  guardar(): void {
    this.intento.set(true);
    const crudo = this.formCompra.getRawValue();
    const conErrores = this.revisarLineas(true).some((e) => e.producto || e.variante || e.cantidad || e.precio);
    if (this.cargandoOferta()) return;
    if (!texto(crudo.proveedor_id) || !texto(crudo.sucursal_id) || crudo.lineas.length === 0 || conErrores) return;

    const datos = {
      proveedor_id: Number(crudo.proveedor_id),
      sucursal_id: Number(crudo.sucursal_id),
      detalle: crudo.lineas.map((l) => ({
        producto_proveedor_id: texto(l.producto_id) ? Number(l.producto_id) : null,
        variante_id: Number(l.variante_id),
        cantidad: Number(texto(l.cantidad)),
        precio_unitario: precioDe(l.precio_unitario),
      })),
    };

    this.guardando.set(true);
    this.http.post<Compra>(`${API_URL}/compras`, datos).subscribe({
      next: (compra) => {
        this.guardando.set(false);
        this.modalNueva.set(false);
        const otraSucursal = compra.sucursal_id !== this.sucursal.id() ? ` Es para ${compra.sucursal}.` : '';
        this.avisos.ok(
          `Compra #${compra.id} a ${compra.proveedor} registrada por Bs ${moneda(compra.total)}: ` +
            `queda pendiente de recibir.${otraSucursal}`,
        );
        this.filtro.set('pendiente');
        this.recargar();
      },
      error: (err) => {
        this.guardando.set(false);
        this.errorServidor.set(mensajeDeError(err, 'No se pudo registrar la compra.'));
      },
    });
  }

  // ------------------------------------------------------ detalle y recepcion
  verDetalle(compra: Compra): void {
    this.conDetalle(compra, (completa) => this.abierta.set(completa));
  }

  pedirRecepcion(compra: Compra): void {
    this.errorRecibir.set(null);
    this.conDetalle(compra, (completa) => {
      this.abierta.set(null);
      this.aRecibir.set(completa);
    });
  }

  private conDetalle(compra: Compra, seguir: (completa: Compra) => void): void {
    if (compra.detalle) {
      seguir(compra);
      return;
    }
    this.cargandoDetalle.set(compra.id);
    this.http.get<Compra>(`${API_URL}/compras/${compra.id}`).subscribe({
      next: (completa) => {
        this.cargandoDetalle.set(null);
        seguir(completa);
      },
      error: (err) => {
        this.cargandoDetalle.set(null);
        this.avisos.error(mensajeDeError(err, `No se pudo abrir la compra #${compra.id}.`));
      },
    });
  }

  confirmarRecepcion(): void {
    const compra = this.aRecibir();
    if (!compra) return;
    this.recibiendo.set(true);
    this.errorRecibir.set(null);
    this.http.post<ResultadoRecepcion>(`${API_URL}/compras/${compra.id}/recibir`, {}).subscribe({
      next: (r) => {
        this.recibiendo.set(false);
        this.aRecibir.set(null);
        const unidades = r.movimientos.reduce((suma, m) => suma + m.cantidad, 0);
        this.avisos.ok(
          `Compra #${r.compra.id} recibida: ` +
            (unidades === 1 ? 'se sumo 1 unidad' : `se sumaron ${unidades} unidades`) +
            ` al stock de ${r.compra.sucursal}. El inventario ya esta actualizado.`,
        );
        this.recargar();
      },
      error: (err: HttpErrorResponse) => {
        this.recibiendo.set(false);
        this.errorRecibir.set(mensajeDeError(err, 'No se pudo recibir la compra.'));
        // Un 400 suele ser una compra que otra persona ya recibio: se actualiza la lista.
        if (err.status === 400) this.recargar();
      },
    });
  }

  cerrarModales(): void {
    if (this.recibiendo()) return;
    this.modalNueva.set(false);
    this.abierta.set(null);
    this.aRecibir.set(null);
  }

  // ----------------------------------------------------------- presentacion
  claseEstado(estado: EstadoCompra): string {
    return estado === 'recibida' ? 'ok' : estado === 'anulada' ? 'bajo' : 'rosa';
  }

  etiquetaEstado(estado: EstadoCompra): string {
    return estado.charAt(0).toUpperCase() + estado.slice(1);
  }

  unidades(compra: Compra): number {
    return (compra.detalle ?? []).reduce((suma, l) => suma + l.cantidad, 0);
  }
}
