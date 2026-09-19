import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { SesionStore } from '../../../core/sesion';
import { OpcionFiltro, SelectorEstado } from '../../../shared/estado/selector-estado';
import { moneda } from '../../../shared/formato';

type EstadoPromo = 'vigente' | 'programada' | 'vencida' | 'inactiva';
type FiltroPromo = EstadoPromo | 'todas';
type TipoDescuento = 'porcentaje' | 'monto';

interface Solapamiento {
  promocion_id: number;
  promocion: string;
  desde: string;
  hasta: string;
  prendas: string[];
}

/** GET /api/promociones (backend: promociones/service.py `salida`). */
interface Promocion {
  id: number;
  nombre: string;
  descripcion: string | null;
  tipo_descuento: TipoDescuento;
  valor: number;
  etiqueta: string;
  fecha_inicio: string;
  fecha_fin: string;
  activo: boolean;
  estado: EstadoPromo;
  prenda_ids: number[];
  prendas: {
    id: number;
    nombre: string;
    imagen_url: string | null;
    precio_venta: number;
    precio_final: number;
    costo: number;
    bajo_costo: boolean;
  }[];
  solapamientos: Solapamiento[];
  advertencia: string | null;
}

/** Lo que se usa de GET /api/prendas para elegir a que prendas se aplica. */
interface PrendaOpcion {
  id: number;
  nombre: string;
  precio_venta: number;
  costo: number;
  imagen_url: string | null;
  activo: boolean | null;
  publicado: boolean;
  categoria_id: number;
}

const FILTROS: OpcionFiltro<FiltroPromo>[] = [
  { valor: 'vigente', etiqueta: 'Vigentes' },
  { valor: 'programada', etiqueta: 'Programadas' },
  { valor: 'vencida', etiqueta: 'Vencidas' },
  { valor: 'inactiva', etiqueta: 'Inactivas' },
  { valor: 'todas', etiqueta: 'Todas' },
];

const NUMERO = /^\d+([.,]\d{1,2})?$/;
const hoyIso = () => {
  const d = new Date();
  const dos = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
};
const masDias = (iso: string, dias: number) => {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + dias);
  return d.toISOString().slice(0, 10);
};

/**
 * CU18 Gestionar promociones. El descuento que se define aca es el que cobran
 * el catalogo, el carrito y la caja mientras la promocion este vigente. Los
 * descuentos no se acumulan: si dos promociones se cruzan sobre una prenda,
 * gana la mayor y la pantalla lo advierte antes y despues de guardar.
 */
@Component({
  selector: 'app-promociones',
  imports: [ReactiveFormsModule, SelectorEstado],
  templateUrl: './promociones.html',
  styleUrl: './promociones.css',
  host: { '(document:keydown.escape)': 'cerrarModales()' },
})
export class Promociones {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);

  readonly filtros = FILTROS;
  readonly moneda = moneda;

  // ---- listado ----
  readonly promociones = signal<Promocion[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);
  readonly filtro = signal<FiltroPromo>('vigente');

  // ---- formulario ----
  readonly prendas = signal<PrendaOpcion[]>([]);
  readonly categorias = signal<{ id: number; nombre: string }[]>([]);
  readonly modal = signal(false);
  readonly editando = signal<Promocion | null>(null);
  readonly guardando = signal(false);
  readonly intento = signal(false);
  readonly errorServidor = signal<string | null>(null);
  readonly elegidas = signal<number[]>([]);
  readonly busquedaPrenda = signal('');
  readonly formulario = this.fb.nonNullable.group({
    nombre: '',
    descripcion: '',
    tipo_descuento: 'porcentaje' as TipoDescuento,
    valor: '',
    fecha_inicio: '',
    fecha_fin: '',
  });
  private readonly valores = toSignal(this.formulario.valueChanges, {
    initialValue: this.formulario.getRawValue(),
  });

  // ---- baja ----
  readonly aEliminar = signal<Promocion | null>(null);
  readonly eliminando = signal(false);
  readonly cambiando = signal<number | null>(null);

  readonly puedeCrear = computed(() => this.sesion.tienePermiso('promociones:crear'));
  readonly puedeEditar = computed(() => this.sesion.tienePermiso('promociones:editar'));
  readonly puedeEliminar = computed(() => this.sesion.tienePermiso('promociones:eliminar'));

  readonly visibles = computed(() =>
    this.filtro() === 'todas' ? this.promociones() : this.promociones().filter((p) => p.estado === this.filtro()),
  );
  readonly conCruces = computed(() => this.promociones().filter((p) => p.solapamientos.length > 0).length);
  readonly pie = computed(() => {
    const n = this.visibles().length;
    return `${n} ${n === 1 ? 'promocion' : 'promociones'}`;
  });

  // ------------------------------------------------- validacion del formulario
  readonly tipo = computed(() => this.valores().tipo_descuento ?? 'porcentaje');
  readonly valorNumero = computed(() => {
    const texto = String(this.valores().valor ?? '').trim();
    return NUMERO.test(texto) ? Number(texto.replace(',', '.')) : null;
  });
  readonly errores = computed(() => {
    const v = this.valores();
    const valor = this.valorNumero();
    const texto = String(v.valor ?? '').trim();
    let errorValor: string | null = null;
    if (!texto) errorValor = 'Falta el valor del descuento.';
    else if (valor === null || valor <= 0) errorValor = 'Es un numero mayor que cero, con hasta 2 decimales.';
    else if (this.tipo() === 'porcentaje' && valor > 90) errorValor = 'Un descuento porcentual va de 1 a 90.';
    return {
      nombre: (v.nombre ?? '').trim() ? null : 'Ponle un nombre a la promocion.',
      valor: errorValor,
      inicio: v.fecha_inicio ? null : 'Falta la fecha de inicio.',
      fin: !v.fecha_fin
        ? 'Falta la fecha de fin.'
        : v.fecha_inicio && v.fecha_fin < v.fecha_inicio
          ? 'No puede terminar antes de empezar.'
          : null,
      prendas: this.elegidas().length > 0 ? null : 'Elegi al menos una prenda.',
    };
  });
  readonly hayErrores = computed(() => Object.values(this.errores()).some((e) => e !== null));

  readonly prendasFiltradas = computed(() => {
    const texto = this.busquedaPrenda().trim().toLowerCase();
    const activas = this.prendas().filter((p) => p.activo !== false || this.elegidas().includes(p.id));
    return texto ? activas.filter((p) => p.nombre.toLowerCase().includes(texto)) : activas;
  });

  /** Como quedaria cada prenda elegida con el descuento que se esta escribiendo. */
  readonly vistaPrevia = computed(() => {
    const valor = this.valorNumero();
    const porId = new Map(this.prendas().map((p) => [p.id, p]));
    return this.elegidas()
      .map((id) => porId.get(id))
      .filter((p): p is PrendaOpcion => !!p)
      .map((p) => {
        const precio = Number(p.precio_venta);
        const rebaja =
          valor === null ? 0 : this.tipo() === 'porcentaje' ? Math.round(precio * valor) / 100 : valor;
        const final = Math.round((precio - rebaja) * 100) / 100;
        return {
          ...p,
          final,
          invalido: final <= 0,
          bajoCosto: final > 0 && final < Number(p.costo),
        };
      });
  });

  /**
   * Cruces que se van a producir si se guarda asi: otras promociones activas que
   * comparten alguna prenda y alguna fecha. El backend vuelve a calcularlo al guardar.
   */
  readonly crucesPrevistos = computed(() => {
    const v = this.valores();
    if (!v.fecha_inicio || !v.fecha_fin || v.fecha_fin < v.fecha_inicio) return [];
    const mia = this.editando()?.id ?? null;
    const elegidas = new Set(this.elegidas());
    return this.promociones()
      .filter((p) => p.id !== mia && p.activo)
      .filter((p) => p.fecha_inicio <= v.fecha_fin! && v.fecha_inicio! <= p.fecha_fin)
      .map((p) => ({ promocion: p, prendas: p.prendas.filter((x) => elegidas.has(x.id)).map((x) => x.nombre) }))
      .filter((c) => c.prendas.length > 0);
  });

  constructor() {
    this.cargar();
    this.http.get<PrendaOpcion[]>(`${API_URL}/prendas`).subscribe({
      next: (filas) => this.prendas.set(filas.sort((a, b) => a.nombre.localeCompare(b.nombre))),
      error: () => this.avisos.error('No se pudieron cargar las prendas para asociarlas.'),
    });
    this.http.get<{ id: number; nombre: string }[]>(`${API_URL}/admin/categorias`).subscribe({
      next: (filas) => this.categorias.set(filas),
      error: () => this.categorias.set([]),
    });
  }

  // ------------------------------------------------------------------ carga
  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set(null);
    this.http.get<Promocion[]>(`${API_URL}/promociones`).subscribe({
      next: (filas) => {
        this.promociones.set(filas);
        this.cargando.set(false);
        // Si no hay vigentes pero si otras, no se abre la pantalla vacia.
        if (this.filtro() === 'vigente' && filas.length > 0 && !filas.some((p) => p.estado === 'vigente')) {
          this.filtro.set('todas');
        }
      },
      error: (err) => {
        this.errorCarga.set(mensajeDeError(err, 'No se pudieron cargar las promociones.'));
        this.cargando.set(false);
      },
    });
  }

  // ------------------------------------------------------------- formulario
  abrirNueva(): void {
    this.editando.set(null);
    this.elegidas.set([]);
    this.formulario.reset({
      nombre: '',
      descripcion: '',
      tipo_descuento: 'porcentaje',
      valor: '',
      fecha_inicio: hoyIso(),
      fecha_fin: masDias(hoyIso(), 7),
    });
    this.abrirModal();
  }

  abrirEdicion(promo: Promocion): void {
    this.editando.set(promo);
    this.elegidas.set([...promo.prenda_ids]);
    this.formulario.reset({
      nombre: promo.nombre,
      descripcion: promo.descripcion ?? '',
      tipo_descuento: promo.tipo_descuento,
      valor: String(promo.valor),
      fecha_inicio: promo.fecha_inicio,
      fecha_fin: promo.fecha_fin,
    });
    this.abrirModal();
  }

  private abrirModal(): void {
    this.intento.set(false);
    this.errorServidor.set(null);
    this.busquedaPrenda.set('');
    this.modal.set(true);
  }

  alternarPrenda(id: number): void {
    this.elegidas.update((ids) => (ids.includes(id) ? ids.filter((i) => i !== id) : [...ids, id]));
    this.errorServidor.set(null);
  }

  elegirCategoria(categoriaId: number): void {
    const deLaCategoria = this.prendas()
      .filter((p) => p.categoria_id === categoriaId && p.activo !== false)
      .map((p) => p.id);
    this.elegidas.update((ids) => [...new Set([...ids, ...deLaCategoria])]);
  }

  readonly categoriasConPrendas = computed(() =>
    this.categorias().filter((c) => this.prendas().some((p) => p.categoria_id === c.id && p.activo !== false)),
  );

  guardar(): void {
    this.intento.set(true);
    if (this.hayErrores()) return;
    const crudo = this.formulario.getRawValue();
    const datos = {
      nombre: crudo.nombre.trim(),
      descripcion: crudo.descripcion.trim() || null,
      tipo_descuento: crudo.tipo_descuento,
      valor: this.valorNumero(),
      fecha_inicio: crudo.fecha_inicio,
      fecha_fin: crudo.fecha_fin,
      prenda_ids: this.elegidas(),
    };
    const promo = this.editando();
    const peticion = promo
      ? this.http.put<Promocion>(`${API_URL}/promociones/${promo.id}`, datos)
      : this.http.post<Promocion>(`${API_URL}/promociones`, datos);

    this.guardando.set(true);
    this.errorServidor.set(null);
    peticion.subscribe({
      next: (guardada) => {
        this.guardando.set(false);
        this.modal.set(false);
        const texto = `Promocion «${guardada.nombre}» ${promo ? 'actualizada' : 'creada'}: ${guardada.etiqueta} en ${
          guardada.prendas.length
        } ${guardada.prendas.length === 1 ? 'prenda' : 'prendas'}.`;
        this.avisos.ok(
          guardada.estado === 'vigente'
            ? `${texto} Ya rige en el catalogo, el carrito y la caja.`
            : `${texto} Queda ${guardada.estado}.`,
        );
        this.avisarCruces(guardada);
        this.filtro.set(guardada.estado);
        this.cargar();
      },
      error: (err) => {
        this.guardando.set(false);
        this.errorServidor.set(mensajeDeError(err, 'No se pudo guardar la promocion.'));
      },
    });
  }

  // --------------------------------------------------------- estado y baja
  cambiarActivo(promo: Promocion, activo: boolean): void {
    this.cambiando.set(promo.id);
    this.http.put<Promocion>(`${API_URL}/promociones/${promo.id}`, { activo }).subscribe({
      next: (p) => {
        this.cambiando.set(null);
        this.avisos.ok(
          activo
            ? `«${p.nombre}» se reactivo y queda ${p.estado}.`
            : `«${p.nombre}» se desactivo: sus prendas vuelven al precio de lista.`,
        );
        this.avisarCruces(p);
        this.cargar();
      },
      error: (err) => {
        this.cambiando.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo cambiar el estado de la promocion.'));
      },
    });
  }

  /** El guardado no se bloquea por un solapamiento, pero tampoco pasa en silencio. */
  private avisarCruces(promo: Promocion): void {
    if (promo.solapamientos.length === 0) return;
    const con = promo.solapamientos.map((c) => `«${c.promocion}» (${c.prendas.join(', ')})`).join(' y ');
    this.avisos.error(
      `Atencion: «${promo.nombre}» se solapa con ${con}. Los descuentos no se acumulan: se cobra el mayor.`,
    );
  }

  confirmarEliminar(): void {
    const promo = this.aEliminar();
    if (!promo) return;
    this.eliminando.set(true);
    this.http.delete<{ detail: string; eliminada: boolean }>(`${API_URL}/promociones/${promo.id}`).subscribe({
      next: (r) => {
        this.eliminando.set(false);
        this.aEliminar.set(null);
        this.avisos.ok(r.detail);
        this.cargar();
      },
      error: (err) => {
        this.eliminando.set(false);
        this.aEliminar.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo eliminar la promocion.'));
      },
    });
  }

  cerrarModales(): void {
    if (this.guardando() || this.eliminando()) return;
    this.modal.set(false);
    this.aEliminar.set(null);
  }

  // ----------------------------------------------------------- presentacion
  claseEstado(estado: EstadoPromo): string {
    return estado === 'vigente' ? 'ok' : estado === 'programada' ? 'rosa' : 'bajo';
  }

  fecha(iso: string): string {
    const [a, m, d] = iso.split('-');
    return `${d}/${m}/${a}`;
  }

  resumenPrendas(promo: Promocion): string {
    const nombres = promo.prendas.map((p) => p.nombre);
    return nombres.length <= 3 ? nombres.join(', ') : `${nombres.slice(0, 3).join(', ')} y ${nombres.length - 3} mas`;
  }
}
