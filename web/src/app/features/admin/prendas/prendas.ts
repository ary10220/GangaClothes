import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { RecursoService, Registro } from '../../../core/recurso.service';
import { esInactivo, filtrarPorEstado, FiltroEstado, textoPie, textoVacio } from '../../../shared/estado/estado';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { moneda } from '../../../shared/formato';
import { erroresStock, FilaStock, filasStock, lineasStock, StockInicial } from './stock-inicial';

const GENEROS = ['unisex', 'mujer', 'hombre', 'nino'];

type FiltroPublicacion = 'todas' | 'publicadas' | 'sin-publicar';

const OPCIONES_PUBLICACION: OpcionFiltro<FiltroPublicacion>[] = [
  { valor: 'todas', etiqueta: 'Todas' },
  { valor: 'publicadas', etiqueta: 'Publicadas' },
  { valor: 'sin-publicar', etiqueta: 'Sin publicar' },
];

/** Stock de una variante en una sucursal (backend: prendas/service.py `variante_salida`). */
interface StockSucursal {
  inventario_id: number;
  sucursal_id: number;
  sucursal: string;
  sucursal_activa: boolean;
  cantidad: number;
  cantidad_reservada: number;
  disponible: number;
  stock_minimo: number;
  stock_maximo: number;
}

interface Variante extends Registro {
  sku: string;
  talla_id: number;
  color_id: number;
  talla: string;
  color: string;
  color_hex: string | null;
  tiene_asset_ar: boolean;
  stock: StockSucursal[];
  stock_total: number;
  disponible_total: number;
}

/**
 * CU7: prendas y sus variantes talla-color, con el ciclo completo para vender:
 * crear la prenda (nace sin publicar) → generar variantes con su stock inicial
 * por sucursal → publicar. Publicar sin stock pide confirmacion.
 */
@Component({
  selector: 'app-prendas',
  imports: [ReactiveFormsModule, RouterLink, SelectorEstado, StockInicial],
  templateUrl: './prendas.html',
  styleUrl: './prendas.css',
  host: { '(document:keydown.escape)': 'cerrarModales()' },
})
export class Prendas {
  private http = inject(HttpClient);
  private recursos = inject(RecursoService);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);

  readonly generos = GENEROS;
  readonly opcionesPublicacion = OPCIONES_PUBLICACION;
  readonly moneda = moneda;

  // ---- listado de prendas ----
  readonly prendas = signal<Registro[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);
  readonly busqueda = signal('');
  readonly estado = signal<FiltroEstado>('activos');
  readonly publicacion = signal<FiltroPublicacion>('todas');

  // ---- catalogos para los selects y las etiquetas ----
  readonly categorias = signal<Registro[]>([]);
  readonly colecciones = signal<Registro[]>([]);
  readonly tallas = signal<Registro[]>([]);
  readonly colores = signal<Registro[]>([]);
  readonly sucursales = signal<Registro[]>([]);

  // ---- prenda abierta y sus variantes ----
  readonly abierta = signal<Registro | null>(null);
  readonly variantes = signal<Variante[]>([]);
  readonly cargandoVariantes = signal(false);

  // ---- formulario de prenda ----
  readonly modalPrenda = signal(false);
  readonly editando = signal<Registro | null>(null);
  readonly guardando = signal(false);
  readonly errorPrenda = signal<string | null>(null);
  formPrenda: FormGroup = this.fb.group({});

  // ---- generador de variantes ----
  readonly generador = signal(false);
  readonly tallasSel = signal<number[]>([]);
  readonly coloresSel = signal<number[]>([]);
  readonly imagenVariantes = signal('');
  readonly filasGenerador = signal<FilaStock[]>([]);
  readonly intentoGenerador = signal(false);
  readonly guardandoVariantes = signal(false);
  readonly errorVariantes = signal<string | null>(null);

  // ---- stock inicial de una variante existente ----
  readonly varianteStock = signal<Variante | null>(null);
  readonly filasCarga = signal<FilaStock[]>([]);
  readonly intentoCarga = signal(false);
  readonly guardandoStock = signal(false);
  readonly errorStock = signal<string | null>(null);

  // ---- recurso AR ----
  readonly varianteAsset = signal<Registro | null>(null);
  readonly guardandoAsset = signal(false);
  readonly errorAsset = signal<string | null>(null);
  formAsset: FormGroup = this.fb.group({});

  // ---- archivar / publicar ----
  readonly cambiandoEstado = signal<number | null>(null);
  /** Prenda que se quiso publicar sin unidades disponibles: espera confirmacion. */
  readonly sinStock = signal<Registro | null>(null);

  readonly enEstado = computed(() => {
    const filas = filtrarPorEstado(this.prendas(), this.estado());
    const filtro = this.publicacion();
    if (filtro === 'todas') return filas;
    return filas.filter((p) => this.publicada(p) === (filtro === 'publicadas'));
  });

  readonly visibles = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    if (!texto) return this.enEstado();
    return this.enEstado().filter((p) =>
      [p['nombre'], p['marca'], this.nombreDe(this.categorias(), p['categoria_id'])]
        .join(' ')
        .toLowerCase()
        .includes(texto),
    );
  });

  readonly archivados = computed(() => this.prendas().filter((p) => esInactivo(p)).length);
  readonly muestraEstado = computed(() => this.estado() === 'todos');
  readonly pie = computed(() => textoPie(this.visibles().length, this.enEstado().length, this.estado(), true));
  readonly mensajeVacio = computed(() => {
    const enEstado = filtrarPorEstado(this.prendas(), this.estado()).length;
    if (enEstado > 0 && this.publicacion() !== 'todas') {
      return this.publicacion() === 'publicadas'
        ? 'Ninguna prenda esta publicada todavia.'
        : 'Todas las prendas estan publicadas.';
    }
    return textoVacio(this.prendas().length, this.archivados(), this.estado(), 'prendas');
  });

  // ---- generador: combinaciones que se van a crear ----
  readonly combinaciones = computed(() => {
    const tallas = this.tallas().filter((t) => this.tallasSel().includes(t.id));
    const colores = this.colores().filter((c) => this.coloresSel().includes(c.id));
    return tallas.flatMap((t) =>
      colores.map((c) => ({
        clave: `${t.id}-${c.id}`,
        texto: `${t['nombre']} · ${c['nombre']}`,
        existe: this.variantes().some((v) => v.talla_id === t.id && v.color_id === c.id),
      })),
    );
  });
  readonly nuevas = computed(() => this.combinaciones().filter((c) => !c.existe).length);

  readonly resumenAbierta = computed(() => {
    const variantes = this.variantes();
    const disponibles = variantes.reduce((s, v) => s + v.disponible_total, 0);
    const sucursales = new Set(variantes.flatMap((v) => v.stock.filter((x) => x.cantidad > 0).map((x) => x.sucursal_id)));
    return { variantes: variantes.length, disponibles, sucursales: sucursales.size };
  });

  constructor() {
    this.cargarCatalogos();
    this.cargar();
  }

  // ------------------------------------------------------------------ carga
  private cargarCatalogos(): void {
    forkJoin({
      categorias: this.recursos.listar('admin/categorias'),
      colecciones: this.recursos.listar('admin/colecciones'),
      tallas: this.recursos.listar('admin/tallas'),
      colores: this.recursos.listar('admin/colores'),
      sucursales: this.recursos.listar('admin/sucursales'),
    }).subscribe({
      next: (r) => {
        this.categorias.set(r.categorias);
        this.colecciones.set(r.colecciones);
        this.tallas.set([...r.tallas].sort((a, b) => Number(a['orden'] ?? 99) - Number(b['orden'] ?? 99)));
        this.colores.set(r.colores);
        this.sucursales.set(r.sucursales.filter((s) => s['activo'] !== false));
      },
      error: () => this.avisos.error('No se pudieron cargar los catalogos base.'),
    });
  }

  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set(null);
    this.http.get<Registro[]>(`${API_URL}/prendas`).subscribe({
      next: (filas) => {
        this.prendas.set(filas);
        this.cargando.set(false);
        // La prenda abierta cambio de estado o de stock: se refresca su copia.
        const abierta = this.abierta();
        if (abierta) this.abierta.set(filas.find((p) => p.id === abierta.id) ?? null);
      },
      error: (err) => {
        this.errorCarga.set(mensajeDeError(err, 'No se pudieron cargar las prendas.'));
        this.cargando.set(false);
      },
    });
  }

  // ------------------------------------------------------------- variantes
  abrir(prenda: Registro): void {
    this.abierta.set(prenda);
    this.cargarVariantes();
    setTimeout(() => document.getElementById('detalle-variantes')?.scrollIntoView({ behavior: 'smooth' }));
  }

  cerrarDetalle(): void {
    this.abierta.set(null);
    this.variantes.set([]);
  }

  cargarVariantes(): void {
    const prenda = this.abierta();
    if (!prenda) return;
    this.cargandoVariantes.set(true);
    this.http.get<Variante[]>(`${API_URL}/prendas/${prenda.id}/variantes`).subscribe({
      next: (filas) => {
        this.variantes.set(filas);
        this.cargandoVariantes.set(false);
      },
      error: () => {
        this.variantes.set([]);
        this.cargandoVariantes.set(false);
        this.avisos.error('No se pudieron cargar las variantes.');
      },
    });
  }

  // ------------------------------------------------------- formulario prenda
  abrirNuevaPrenda(): void {
    this.editando.set(null);
    this.errorPrenda.set(null);
    this.formPrenda = this.construirFormPrenda(null);
    this.modalPrenda.set(true);
  }

  abrirEdicionPrenda(prenda: Registro): void {
    this.editando.set(prenda);
    this.errorPrenda.set(null);
    this.formPrenda = this.construirFormPrenda(prenda);
    this.modalPrenda.set(true);
  }

  private construirFormPrenda(p: Registro | null): FormGroup {
    const texto = (clave: string) => (p?.[clave] === null || p?.[clave] === undefined ? '' : String(p[clave]));
    return this.fb.group({
      nombre: [texto('nombre'), Validators.required],
      categoria_id: [texto('categoria_id'), Validators.required],
      coleccion_id: [texto('coleccion_id')],
      marca: [texto('marca')],
      genero: [texto('genero')],
      precio_venta: [texto('precio_venta'), [Validators.required, Validators.min(0)]],
      costo: [texto('costo'), [Validators.required, Validators.min(0)]],
      imagen_url: [texto('imagen_url')],
      descripcion: [texto('descripcion')],
    });
  }

  invalidoPrenda(campo: string): boolean {
    const control = this.formPrenda.get(campo);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  guardarPrenda(): void {
    if (this.formPrenda.invalid) {
      this.formPrenda.markAllAsTouched();
      return;
    }
    this.errorPrenda.set(null);
    this.guardando.set(true);

    const crudo = this.formPrenda.getRawValue();
    const numero = (v: unknown) => (v === '' || v === null ? null : Number(v));
    const datos = {
      nombre: crudo.nombre,
      categoria_id: numero(crudo.categoria_id),
      coleccion_id: numero(crudo.coleccion_id),
      marca: crudo.marca || null,
      genero: crudo.genero || null,
      precio_venta: numero(crudo.precio_venta),
      costo: numero(crudo.costo),
      imagen_url: crudo.imagen_url || null,
      descripcion: crudo.descripcion || null,
    };

    const editando = this.editando();
    const peticion = editando
      ? this.http.put<Registro>(`${API_URL}/prendas/${editando.id}`, datos)
      : this.http.post<Registro>(`${API_URL}/prendas`, datos);

    peticion.subscribe({
      next: (prenda) => {
        this.guardando.set(false);
        this.modalPrenda.set(false);
        this.cargar();
        if (editando) {
          this.avisos.ok('Se actualizo la prenda.');
          return;
        }
        // Siguiente paso natural: sus variantes con el stock de cada sucursal.
        this.avisos.ok(`Se creo «${prenda['nombre']}» sin publicar. Ahora genera sus variantes y carga su stock.`);
        this.abrir(prenda);
        this.abrirGenerador();
      },
      error: (err) => {
        this.guardando.set(false);
        this.errorPrenda.set(mensajeDeError(err, 'No se pudo guardar la prenda.'));
      },
    });
  }

  /** La API de prendas no expone DELETE: archivar es un PUT sobre `activo`. */
  cambiarEstado(prenda: Registro, activo: boolean): void {
    this.cambiandoEstado.set(prenda.id);
    this.http.put<Registro>(`${API_URL}/prendas/${prenda.id}`, { activo }).subscribe({
      next: () => {
        this.cambiandoEstado.set(null);
        this.avisos.ok(
          activo
            ? 'Se reactivo la prenda. Sigue sin publicar hasta que la publiques.'
            : this.publicada(prenda)
              ? 'Se archivo la prenda y se retiro de la tienda en linea.'
              : 'Se archivo la prenda.',
        );
        this.cargar();
      },
      error: (err) => {
        this.cambiandoEstado.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo cambiar el estado de la prenda.'));
      },
    });
  }

  // ------------------------------------------------------------ publicacion
  publicar(prenda: Registro, confirmarSinStock = false): void {
    if (!confirmarSinStock && Number(prenda['disponible_total'] ?? 0) <= 0) {
      this.sinStock.set(prenda);
      return;
    }
    this.cambiandoEstado.set(prenda.id);
    this.http
      .post<Registro>(`${API_URL}/prendas/${prenda.id}/publicar`, { confirmar_sin_stock: confirmarSinStock })
      .subscribe({
        next: (actualizada) => {
          this.cambiandoEstado.set(null);
          this.sinStock.set(null);
          this.avisos.ok(
            confirmarSinStock
              ? `«${actualizada['nombre']}» esta publicada, pero se vera agotada hasta que tenga stock.`
              : `«${actualizada['nombre']}» ya se ve en la tienda con ${actualizada['disponible_total']} unidades disponibles.`,
          );
          this.cargar();
        },
        error: (err) => {
          this.cambiandoEstado.set(null);
          // 409: el stock se acabo entre la carga de la tabla y el clic.
          if (err.status === 409) this.sinStock.set(prenda);
          else this.avisos.error(mensajeDeError(err, 'No se pudo publicar la prenda.'));
        },
      });
  }

  despublicar(prenda: Registro): void {
    this.cambiandoEstado.set(prenda.id);
    this.http.post<Registro>(`${API_URL}/prendas/${prenda.id}/despublicar`, {}).subscribe({
      next: () => {
        this.cambiandoEstado.set(null);
        this.avisos.ok(`«${prenda['nombre']}» se retiro de la tienda en linea. Sigue disponible en caja.`);
        this.cargar();
      },
      error: (err) => {
        this.cambiandoEstado.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo despublicar la prenda.'));
      },
    });
  }

  /** Desde el aviso de "sin stock": lleva a donde se carga. */
  irACargarStock(): void {
    const prenda = this.sinStock();
    if (!prenda) return;
    this.sinStock.set(null);
    this.abrir(prenda);
    if (Number(prenda['variantes'] ?? 0) === 0) this.abrirGenerador();
  }

  // --------------------------------------------------- generador de variantes
  abrirGenerador(): void {
    this.tallasSel.set([]);
    this.coloresSel.set([]);
    this.imagenVariantes.set('');
    this.filasGenerador.set(filasStock(this.opcionesSucursal()));
    this.intentoGenerador.set(false);
    this.errorVariantes.set(null);
    this.generador.set(true);
  }

  alternarTalla(id: number): void {
    this.tallasSel.update((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  }

  alternarColor(id: number): void {
    this.coloresSel.update((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  }

  sucursalesMarcadas(filas: FilaStock[]): string {
    return filas.filter((f) => f.cargar).map((f) => f.sucursal).join(' y ');
  }

  generarVariantes(): void {
    const prenda = this.abierta();
    if (!prenda) return;
    this.intentoGenerador.set(true);
    if (this.nuevas() === 0 || Object.keys(erroresStock(this.filasGenerador())).length > 0) return;

    this.errorVariantes.set(null);
    this.guardandoVariantes.set(true);
    const stock = lineasStock(this.filasGenerador());
    const datos = {
      talla_ids: this.tallasSel(),
      color_ids: this.coloresSel(),
      imagen_url: this.imagenVariantes().trim() || null,
      stock_inicial: stock,
    };

    this.http
      .post<{ creadas: Variante[]; omitidas: string[] }>(`${API_URL}/prendas/${prenda.id}/variantes/lote`, datos)
      .subscribe({
        next: (r) => {
          this.guardandoVariantes.set(false);
          this.generador.set(false);
          const cuantas = r.creadas.length === 1 ? '1 variante' : `${r.creadas.length} variantes`;
          this.avisos.ok(
            stock.length
              ? `Se crearon ${cuantas} con stock en ${this.sucursalesMarcadas(this.filasGenerador())}.`
              : `Se crearon ${cuantas} sin stock. Cargalo con «Cargar stock» antes de publicar.`,
          );
          this.cargarVariantes();
          this.cargar();
        },
        error: (err) => {
          this.guardandoVariantes.set(false);
          this.errorVariantes.set(mensajeDeError(err, 'No se pudieron crear las variantes.'));
        },
      });
  }

  // ------------------------------------------------ stock de variante existente
  /** Sucursales activas donde la variante todavia no tiene stock registrado. */
  sucursalesSinRegistro(variante: Variante): { id: number; nombre: string }[] {
    return this.opcionesSucursal().filter((s) => !variante.stock.some((x) => x.sucursal_id === s.id));
  }

  abrirCargaStock(variante: Variante): void {
    this.filasCarga.set(filasStock(this.sucursalesSinRegistro(variante)).map((f, i) => ({ ...f, cargar: i === 0 })));
    this.intentoCarga.set(false);
    this.errorStock.set(null);
    this.varianteStock.set(variante);
  }

  guardarStock(): void {
    const variante = this.varianteStock();
    if (!variante) return;
    this.intentoCarga.set(true);
    const lineas = lineasStock(this.filasCarga());
    if (lineas.length === 0) {
      this.errorStock.set('Marca al menos una sucursal.');
      return;
    }
    if (Object.keys(erroresStock(this.filasCarga())).length > 0) return;

    this.errorStock.set(null);
    this.guardandoStock.set(true);
    this.http
      .post<Variante>(`${API_URL}/prendas/variantes/${variante.id}/stock-inicial`, { sucursales: lineas })
      .subscribe({
        next: (v) => {
          this.guardandoStock.set(false);
          this.varianteStock.set(null);
          this.avisos.ok(
            `Stock inicial de ${v.sku} cargado en ${this.sucursalesMarcadas(this.filasCarga())}. ` +
              'Quedo registrado en Movimientos.',
          );
          this.cargarVariantes();
          this.cargar();
        },
        error: (err) => {
          this.guardandoStock.set(false);
          this.errorStock.set(mensajeDeError(err, 'No se pudo cargar el stock.'));
        },
      });
  }

  // -------------------------------------------------------- recurso AR (CU24)
  abrirAsset(variante: Registro): void {
    this.errorAsset.set(null);
    this.formAsset = this.fb.group({
      tipo: ['png_overlay', Validators.required],
      url_recurso: ['', Validators.required],
      escala: ['1', [Validators.required, Validators.min(0.01)]],
    });
    this.varianteAsset.set(variante);
  }

  invalidoAsset(campo: string): boolean {
    const control = this.formAsset.get(campo);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  guardarAsset(): void {
    const variante = this.varianteAsset();
    if (!variante) return;
    if (this.formAsset.invalid) {
      this.formAsset.markAllAsTouched();
      return;
    }
    this.errorAsset.set(null);
    this.guardandoAsset.set(true);

    const crudo = this.formAsset.getRawValue();
    const datos = { tipo: crudo.tipo, url_recurso: crudo.url_recurso, escala: Number(crudo.escala) };

    this.http.post(`${API_URL}/prendas/variantes/${variante.id}/asset-ar`, datos).subscribe({
      next: () => {
        this.guardandoAsset.set(false);
        this.varianteAsset.set(null);
        this.avisos.ok(`Recurso AR registrado para ${variante['sku']}.`);
        this.cargarVariantes();
      },
      error: (err) => {
        this.guardandoAsset.set(false);
        this.errorAsset.set(mensajeDeError(err, 'No se pudo registrar el recurso.'));
      },
    });
  }

  cerrarModales(): void {
    this.modalPrenda.set(false);
    this.generador.set(false);
    this.varianteStock.set(null);
    this.varianteAsset.set(null);
    this.sinStock.set(null);
  }

  // ------------------------------------------------------------ presentacion
  nombreDe(lista: Registro[], id: unknown): string {
    if (id === null || id === undefined || id === '') return '—';
    return String(lista.find((f) => f.id === Number(id))?.['nombre'] ?? `#${id}`);
  }

  opcionesSucursal(): { id: number; nombre: string }[] {
    return this.sucursales().map((s) => ({ id: s.id, nombre: String(s['nombre']) }));
  }

  hex(valor: unknown): string {
    const hex = String(valor ?? '');
    return /^#[0-9a-f]{6}$/i.test(hex) ? hex : '#CCCCCC';
  }

  margen(prenda: Registro): number {
    return Number(prenda['precio_venta'] ?? 0) - Number(prenda['costo'] ?? 0);
  }

  esInactiva(prenda: Registro): boolean {
    return esInactivo(prenda);
  }

  publicada(prenda: Registro): boolean {
    return prenda['publicado'] === true;
  }

  numero(valor: unknown): number {
    return Number(valor ?? 0);
  }
}
