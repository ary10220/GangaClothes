import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { RecursoService, Registro } from '../../../core/recurso.service';
import { esInactivo, filtrarPorEstado, FiltroEstado, textoPie, textoVacio } from '../../../shared/estado/estado';
import { SelectorEstado } from '../../../shared/estado/selector-estado';

const GENEROS = ['unisex', 'mujer', 'hombre', 'nino'];

/**
 * CU7: administracion de prendas y sus variantes talla-color.
 * No usa la fabrica generica: el backend tiene su propio router con SKU
 * autogenerado, sub-recurso de variantes y registro de recursos del probador.
 */
@Component({
  selector: 'app-prendas',
  imports: [ReactiveFormsModule, SelectorEstado],
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

  // ---- listado de prendas ----
  readonly prendas = signal<Registro[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);
  readonly busqueda = signal('');
  readonly estado = signal<FiltroEstado>('activos');

  // ---- catalogos para los selects y las etiquetas ----
  readonly categorias = signal<Registro[]>([]);
  readonly colecciones = signal<Registro[]>([]);
  readonly tallas = signal<Registro[]>([]);
  readonly colores = signal<Registro[]>([]);

  // ---- prenda abierta y sus variantes ----
  readonly abierta = signal<Registro | null>(null);
  readonly variantes = signal<Registro[]>([]);
  readonly cargandoVariantes = signal(false);

  // ---- formulario de prenda ----
  readonly modalPrenda = signal(false);
  readonly editando = signal<Registro | null>(null);
  readonly guardando = signal(false);
  readonly errorPrenda = signal<string | null>(null);
  formPrenda: FormGroup = this.fb.group({});

  // ---- formulario de variante ----
  readonly modalVariante = signal(false);
  readonly guardandoVariante = signal(false);
  readonly errorVariante = signal<string | null>(null);
  formVariante: FormGroup = this.fb.group({});

  // ---- formulario de recurso AR ----
  readonly varianteAsset = signal<Registro | null>(null);
  readonly guardandoAsset = signal(false);
  readonly errorAsset = signal<string | null>(null);
  formAsset: FormGroup = this.fb.group({});

  // ---- archivar / reactivar ----
  readonly cambiandoEstado = signal<number | null>(null);

  readonly enEstado = computed(() => filtrarPorEstado(this.prendas(), this.estado()));

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
  readonly mensajeVacio = computed(() =>
    textoVacio(this.prendas().length, this.archivados(), this.estado(), 'prendas'),
  );

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
    }).subscribe({
      next: (r) => {
        this.categorias.set(r.categorias);
        this.colecciones.set(r.colecciones);
        this.tallas.set(r.tallas);
        this.colores.set(r.colores);
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
        // Si la prenda abierta cambio de estado, se refresca su copia.
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
  }

  cerrarDetalle(): void {
    this.abierta.set(null);
    this.variantes.set([]);
  }

  cargarVariantes(): void {
    const prenda = this.abierta();
    if (!prenda) return;
    this.cargandoVariantes.set(true);
    this.http.get<Registro[]>(`${API_URL}/prendas/${prenda.id}/variantes`).subscribe({
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
      next: () => {
        this.guardando.set(false);
        this.modalPrenda.set(false);
        this.avisos.ok(editando ? 'Se actualizo la prenda.' : 'Se creo la prenda.');
        this.cargar();
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
        this.avisos.ok(activo ? 'Se reactivo la prenda.' : 'Se archivo la prenda.');
        this.cargar();
      },
      error: (err) => {
        this.cambiandoEstado.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo cambiar el estado de la prenda.'));
      },
    });
  }

  // ----------------------------------------------------- formulario variante
  abrirNuevaVariante(): void {
    this.errorVariante.set(null);
    this.formVariante = this.fb.group({
      talla_id: ['', Validators.required],
      color_id: ['', Validators.required],
      imagen_url: [''],
    });
    this.modalVariante.set(true);
  }

  invalidoVariante(campo: string): boolean {
    const control = this.formVariante.get(campo);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  guardarVariante(): void {
    const prenda = this.abierta();
    if (!prenda) return;
    if (this.formVariante.invalid) {
      this.formVariante.markAllAsTouched();
      return;
    }
    this.errorVariante.set(null);
    this.guardandoVariante.set(true);

    const crudo = this.formVariante.getRawValue();
    const datos = {
      talla_id: Number(crudo.talla_id),
      color_id: Number(crudo.color_id),
      imagen_url: crudo.imagen_url || null,
    };

    this.http.post<Registro>(`${API_URL}/prendas/${prenda.id}/variantes`, datos).subscribe({
      next: (v) => {
        this.guardandoVariante.set(false);
        this.modalVariante.set(false);
        this.avisos.ok(`Se creo la variante ${v['sku']}.`);
        this.cargarVariantes();
      },
      error: (err) => {
        this.guardandoVariante.set(false);
        // El backend devuelve 400 si la combinacion talla-color ya existe.
        this.errorVariante.set(
          err.status === 400
            ? `Ya existe una variante de esta prenda con talla ${this.nombreDe(this.tallas(), datos.talla_id)} y ` +
                `color ${this.nombreDe(this.colores(), datos.color_id)}. Elegi otra combinacion.`
            : mensajeDeError(err, 'No se pudo crear la variante.'),
        );
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
    this.modalVariante.set(false);
    this.varianteAsset.set(null);
  }

  // ------------------------------------------------------------ presentacion
  nombreDe(lista: Registro[], id: unknown): string {
    if (id === null || id === undefined || id === '') return '—';
    return String(lista.find((f) => f.id === Number(id))?.['nombre'] ?? `#${id}`);
  }

  hexDeColor(id: unknown): string {
    const color = this.colores().find((c) => c.id === Number(id));
    const hex = String(color?.['codigo_hex'] ?? '');
    return /^#[0-9a-f]{6}$/i.test(hex) ? hex : '#CCCCCC';
  }

  /** Formato boliviano: coma decimal, como en el mockup. */
  moneda(valor: unknown): string {
    const n = Number(valor ?? 0);
    return n.toFixed(2).replace('.', ',');
  }

  margen(prenda: Registro): number {
    return Number(prenda['precio_venta'] ?? 0) - Number(prenda['costo'] ?? 0);
  }

  esInactiva(prenda: Registro): boolean {
    return esInactivo(prenda);
  }

  tieneAsset(variante: Registro): boolean {
    return variante['tiene_asset_ar'] === true;
  }
}
