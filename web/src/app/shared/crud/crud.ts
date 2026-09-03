import { TitleCasePipe } from '@angular/common';
import { Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';

import { mensajeDeError } from '../../core/errores.interceptor';
import { Notificaciones } from '../../core/notificaciones';
import { RecursoService, Registro } from '../../core/recurso.service';
import { esInactivo, filtrarPorEstado, FiltroEstado, textoPie, textoVacio } from '../estado/estado';
import { SelectorEstado } from '../estado/selector-estado';
import { CampoCrud, ConfigCrud, Opcion } from './config';

/** Un hex de 3 digitos (#D33) no sirve para <input type="color">: se expande a 6. */
function normalizarHex(valor: unknown): string {
  const texto = String(valor ?? '').trim();
  const corto = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/i.exec(texto);
  if (corto) return `#${corto[1]}${corto[1]}${corto[2]}${corto[2]}${corto[3]}${corto[3]}`;
  return /^#[0-9a-f]{6}$/i.test(texto) ? texto : '#000000';
}

/**
 * Pantalla CRUD reutilizable para los catalogos que el backend genera con la
 * fabrica `modules/comunes.py`. Todo lo especifico de cada recurso viene en
 * `config`, que llega desde el `data` de la ruta.
 */
@Component({
  selector: 'app-crud',
  imports: [ReactiveFormsModule, TitleCasePipe, SelectorEstado],
  templateUrl: './crud.html',
  styleUrl: './crud.css',
  host: { '(document:keydown.escape)': 'cerrarTodo()' },
})
export class Crud {
  readonly config = input.required<ConfigCrud>();

  private fb = inject(FormBuilder);
  private recursos = inject(RecursoService);
  private avisos = inject(Notificaciones);

  // ---- listado ----
  readonly filas = signal<Registro[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);
  readonly busqueda = signal('');
  readonly estado = signal<FiltroEstado>('activos');
  /** Opciones de los campos select, indexadas por nombre de campo. */
  readonly opciones = signal<Record<string, Opcion[]>>({});

  // ---- formulario ----
  readonly modalAbierto = signal(false);
  readonly editando = signal<Registro | null>(null);
  readonly guardando = signal(false);
  readonly errorFormulario = signal<string | null>(null);
  formulario: FormGroup = this.fb.group({});

  // ---- borrado / reactivacion ----
  readonly aEliminar = signal<Registro | null>(null);
  readonly eliminando = signal(false);
  readonly errorEliminar = signal<string | null>(null);
  /** Id de la fila que se esta reactivando, para deshabilitar solo ese boton. */
  readonly reactivando = signal<number | null>(null);

  readonly camposTabla = computed(() => this.config().campos.filter((c) => c.enTabla !== false));
  /** `singular` lleva articulo para los mensajes ("se creo la categoria");
   *  el titulo del modal lo necesita sin el. */
  readonly encabezado = computed(() => this.config().singular.replace(/^(el|la|los|las)\s+/i, ''));
  /** Solo los recursos con columna `activo` ofrecen el filtro de estado. */
  readonly archivable = computed(() => this.config().archivable === true);
  /** La columna Estado solo aporta en "Todos": en las otras vistas es una constante. */
  readonly muestraEstado = computed(() => this.archivable() && this.estado() === 'todos');

  /** Filas del estado elegido, antes de aplicar la busqueda. */
  readonly enEstado = computed(() =>
    this.archivable() ? filtrarPorEstado(this.filas(), this.estado()) : this.filas(),
  );

  readonly visibles = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    const lista = this.enEstado();
    if (!texto) return lista;
    return lista.filter((fila) =>
      this.camposTabla()
        .map((campo) => this.textoCelda(fila, campo))
        .join(' ')
        .toLowerCase()
        .includes(texto),
    );
  });

  readonly archivados = computed(() => this.filas().filter((f) => esInactivo(f)).length);

  readonly pie = computed(() =>
    textoPie(this.visibles().length, this.enEstado().length, this.estado(), this.archivable()),
  );

  readonly mensajeVacio = computed(() =>
    textoVacio(this.filas().length, this.archivados(), this.estado(), this.config().titulo),
  );

  constructor() {
    // Las 7 pantallas comparten instancia de componente: al cambiar de ruta
    // solo cambia `config`, asi que hay que reiniciar todo el estado.
    effect(() => {
      const cfg = this.config();
      untracked(() => this.iniciar(cfg));
    });
  }

  // ------------------------------------------------------------------ carga
  private iniciar(cfg: ConfigCrud): void {
    this.filas.set([]);
    this.busqueda.set('');
    this.estado.set('activos');
    this.cerrarTodo();
    this.cargarOpciones(cfg);
    this.cargar();
  }

  private cargarOpciones(cfg: ConfigCrud): void {
    const conOrigen = cfg.campos.filter((c) => c.origen);
    if (conOrigen.length === 0) {
      this.opciones.set({});
      return;
    }
    forkJoin(conOrigen.map((campo) => this.recursos.listar(campo.origen!.ruta))).subscribe({
      next: (respuestas) => {
        const mapa: Record<string, Opcion[]> = {};
        conOrigen.forEach((campo, i) => {
          const clave = campo.origen!.etiqueta ?? 'nombre';
          mapa[campo.nombre] = respuestas[i].map((fila) => ({
            id: fila.id,
            etiqueta: String(fila[clave] ?? `#${fila.id}`),
          }));
        });
        this.opciones.set(mapa);
      },
      error: () => this.opciones.set({}),
    });
  }

  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set(null);
    this.recursos.listar(this.config().ruta).subscribe({
      next: (filas) => {
        this.filas.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        this.errorCarga.set(mensajeDeError(err, 'No se pudo cargar la informacion.'));
        this.cargando.set(false);
      },
    });
  }

  // ------------------------------------------------------------- formulario
  abrirNuevo(): void {
    this.editando.set(null);
    this.errorFormulario.set(null);
    this.formulario = this.construirFormulario(null);
    this.modalAbierto.set(true);
  }

  abrirEdicion(fila: Registro): void {
    this.editando.set(fila);
    this.errorFormulario.set(null);
    this.formulario = this.construirFormulario(fila);
    this.modalAbierto.set(true);
  }

  private construirFormulario(fila: Registro | null): FormGroup {
    const controles: Record<string, unknown[]> = {};
    for (const campo of this.config().campos) {
      const bruto = fila ? fila[campo.nombre] : null;
      const valor =
        campo.tipo === 'color'
          ? normalizarHex(bruto ?? '#000000')
          : bruto === null || bruto === undefined
            ? ''
            : String(bruto);
      controles[campo.nombre] = [valor, campo.requerido ? [Validators.required] : []];
    }
    return this.fb.group(controles);
  }

  invalido(campo: CampoCrud): boolean {
    const control = this.formulario.get(campo.nombre);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  guardar(): void {
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }
    this.errorFormulario.set(null);
    this.guardando.set(true);

    const cfg = this.config();
    const datos = this.aPayload();
    const fila = this.editando();
    const peticion = fila
      ? this.recursos.actualizar(cfg.ruta, fila.id, datos)
      : this.recursos.crear(cfg.ruta, datos);

    peticion.subscribe({
      next: () => {
        this.guardando.set(false);
        this.modalAbierto.set(false);
        this.avisos.ok(fila ? `Se actualizo ${cfg.singular}.` : `Se creo ${cfg.singular}.`);
        this.cargar();
      },
      error: (err) => {
        this.guardando.set(false);
        // El 400 de la fabrica es "Registro duplicado o referencia inexistente":
        // se muestra dentro del modal, junto al formulario que lo provoco.
        this.errorFormulario.set(mensajeDeError(err, 'No se pudo guardar. Revisa los datos.'));
      },
    });
  }

  /** Convierte los valores del formulario (siempre texto) a lo que espera la API. */
  private aPayload(): Record<string, unknown> {
    const crudo = this.formulario.getRawValue();
    const salida: Record<string, unknown> = {};
    for (const campo of this.config().campos) {
      const valor = crudo[campo.nombre];
      if (valor === '' || valor === null || valor === undefined) {
        salida[campo.nombre] = null;
      } else if (campo.tipo === 'numero' || campo.tipo === 'select') {
        salida[campo.nombre] = Number(valor);
      } else {
        salida[campo.nombre] = valor;
      }
    }
    return salida;
  }

  // ---------------------------------------------------------------- borrado
  pedirBorrado(fila: Registro): void {
    this.errorEliminar.set(null);
    this.aEliminar.set(fila);
  }

  confirmarBorrado(): void {
    const fila = this.aEliminar();
    if (!fila) return;
    this.eliminando.set(true);
    this.errorEliminar.set(null);
    this.recursos.eliminar(this.config().ruta, fila.id).subscribe({
      next: (respuesta) => {
        this.eliminando.set(false);
        this.aEliminar.set(null);
        // El backend responde "eliminado" o "tiene registros asociados: se
        // desactivo en su lugar"; mostramos su propio texto tal cual.
        this.avisos.ok(respuesta.detail);
        this.cargar();
      },
      error: (err) => {
        this.eliminando.set(false);
        this.errorEliminar.set(mensajeDeError(err, 'No se pudo eliminar el registro.'));
      },
    });
  }

  /** Devuelve una fila archivada a la vista de activos. */
  reactivar(fila: Registro): void {
    this.reactivando.set(fila.id);
    this.recursos.actualizar(this.config().ruta, fila.id, { activo: true }).subscribe({
      next: () => {
        this.reactivando.set(null);
        this.avisos.ok(`Se reactivo ${this.config().singular}.`);
        this.cargar();
      },
      error: (err) => {
        this.reactivando.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo reactivar el registro.'));
      },
    });
  }

  cerrarTodo(): void {
    this.modalAbierto.set(false);
    this.aEliminar.set(null);
  }

  // ----------------------------------------------------------- presentacion
  /** Texto que va en una celda de la tabla. */
  textoCelda(fila: Registro, campo: CampoCrud): string {
    const valor = fila[campo.nombre];
    if (valor === null || valor === undefined || valor === '') return '—';
    if (campo.tipo === 'select') {
      const opcion = (this.opciones()[campo.nombre] ?? []).find((o) => o.id === Number(valor));
      return opcion?.etiqueta ?? `#${valor}`;
    }
    if (campo.tipo === 'fecha') {
      const [anio, mes, dia] = String(valor).slice(0, 10).split('-');
      return dia ? `${dia}/${mes}/${anio}` : String(valor);
    }
    return String(valor);
  }

  hex(fila: Registro, campo: CampoCrud): string {
    return normalizarHex(fila[campo.nombre]);
  }

  esInactivo(fila: Registro): boolean {
    return esInactivo(fila);
  }

  /** Nombre legible de una fila, para el mensaje de confirmacion. */
  titulo(fila: Registro): string {
    return String(fila['nombre'] ?? `#${fila.id}`);
  }
}
