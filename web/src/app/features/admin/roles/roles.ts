import { LowerCasePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin } from 'rxjs';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';

export interface PermisoItem {
  codigo: string;
  accion: string;
  nombre: string;
  descripcion: string | null;
}

export interface ModuloPermisos {
  modulo: string;
  etiqueta: string;
  descripcion: string;
  permisos: PermisoItem[];
}

export interface RolDetalle {
  id: number;
  nombre: string;
  descripcion: string | null;
  activo: boolean;
  usuarios: number;
  permisos: string[];
  /** El rol administrador es inmutable para no quedarse sin acceso. */
  editable: boolean;
}

/**
 * Roles y permisos: por cada rol se marca que acciones puede hacer en cada
 * modulo del sistema. Lo que se guarda aqui es lo que el backend valida en
 * cada endpoint, no es informativo.
 */
@Component({
  selector: 'app-roles',
  imports: [ReactiveFormsModule, LowerCasePipe],
  templateUrl: './roles.html',
  styleUrl: './roles.css',
  host: { '(document:keydown.escape)': 'cerrarModales()' },
})
export class Roles {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);

  readonly modulos = signal<ModuloPermisos[]>([]);
  readonly roles = signal<RolDetalle[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  /** Rol abierto en el editor de permisos. */
  readonly abierto = signal<RolDetalle | null>(null);
  /** Permisos marcados en el editor, antes de guardar. */
  readonly elegidos = signal<Set<string>>(new Set());
  readonly guardando = signal(false);

  // ---- alta de rol ----
  readonly modalNuevo = signal(false);
  readonly creando = signal(false);
  readonly errorNuevo = signal<string | null>(null);
  formNuevo: FormGroup = this.fb.group({});

  // ---- baja de rol ----
  readonly aEliminar = signal<RolDetalle | null>(null);
  readonly eliminando = signal(false);
  readonly errorEliminar = signal<string | null>(null);

  readonly totalPermisos = computed(() =>
    this.modulos().reduce((total, m) => total + m.permisos.length, 0),
  );

  readonly hayCambios = computed(() => {
    const rol = this.abierto();
    if (!rol) return false;
    const antes = [...rol.permisos].sort().join('|');
    const ahora = [...this.elegidos()].sort().join('|');
    return antes !== ahora;
  });

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    forkJoin({
      modulos: this.http.get<ModuloPermisos[]>(`${API_URL}/seguridad/permisos`),
      roles: this.http.get<RolDetalle[]>(`${API_URL}/seguridad/roles`),
    }).subscribe({
      next: (r) => {
        this.modulos.set(r.modulos);
        this.roles.set(r.roles);
        this.cargando.set(false);
        // Si habia un rol abierto, se vuelve a apuntar a su version fresca.
        const abierto = this.abierto();
        if (abierto) {
          const actualizado = r.roles.find((x) => x.id === abierto.id) ?? null;
          this.abierto.set(actualizado);
          this.elegidos.set(new Set(actualizado?.permisos ?? []));
        }
      },
      error: (err) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar los roles.'));
        this.cargando.set(false);
      },
    });
  }

  // ------------------------------------------------------- editor de permisos
  abrir(rol: RolDetalle): void {
    this.abierto.set(rol);
    this.elegidos.set(new Set(rol.permisos));
  }

  cerrarEditor(): void {
    this.abierto.set(null);
    this.elegidos.set(new Set());
  }

  marcado(codigo: string): boolean {
    return this.elegidos().has(codigo);
  }

  alternar(codigo: string): void {
    if (!this.abierto()?.editable) return;
    this.elegidos.update((actuales) => {
      const copia = new Set(actuales);
      copia.has(codigo) ? copia.delete(codigo) : copia.add(codigo);
      return copia;
    });
  }

  /** Marca o desmarca de una vez todas las acciones de un modulo. */
  alternarModulo(modulo: ModuloPermisos): void {
    if (!this.abierto()?.editable) return;
    const codigos = modulo.permisos.map((p) => p.codigo);
    const completo = codigos.every((c) => this.elegidos().has(c));
    this.elegidos.update((actuales) => {
      const copia = new Set(actuales);
      for (const c of codigos) completo ? copia.delete(c) : copia.add(c);
      return copia;
    });
  }

  marcadosEn(modulo: ModuloPermisos): number {
    return modulo.permisos.filter((p) => this.elegidos().has(p.codigo)).length;
  }

  moduloCompleto(modulo: ModuloPermisos): boolean {
    return this.marcadosEn(modulo) === modulo.permisos.length;
  }

  guardar(): void {
    const rol = this.abierto();
    if (!rol || !rol.editable) return;
    this.guardando.set(true);
    this.http
      .put<RolDetalle>(`${API_URL}/seguridad/roles/${rol.id}`, { permisos: [...this.elegidos()] })
      .subscribe({
        next: () => {
          this.guardando.set(false);
          this.avisos.ok(`Permisos del rol ${rol.nombre} actualizados.`);
          this.cargar();
        },
        error: (err) => {
          this.guardando.set(false);
          this.avisos.error(mensajeDeError(err, 'No se pudieron guardar los permisos.'));
        },
      });
  }

  descartar(): void {
    const rol = this.abierto();
    if (rol) this.elegidos.set(new Set(rol.permisos));
  }

  // -------------------------------------------------------------- alta / baja
  abrirNuevo(): void {
    this.errorNuevo.set(null);
    this.formNuevo = this.fb.group({
      nombre: ['', [Validators.required, Validators.minLength(3)]],
      descripcion: [''],
    });
    this.modalNuevo.set(true);
  }

  invalidoNuevo(campo: string): boolean {
    const control = this.formNuevo.get(campo);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  crear(): void {
    if (this.formNuevo.invalid) {
      this.formNuevo.markAllAsTouched();
      return;
    }
    this.errorNuevo.set(null);
    this.creando.set(true);
    const crudo = this.formNuevo.getRawValue();
    this.http
      .post<RolDetalle>(`${API_URL}/seguridad/roles`, {
        nombre: crudo.nombre,
        descripcion: crudo.descripcion || null,
        permisos: [],
      })
      .subscribe({
        next: (rol) => {
          this.creando.set(false);
          this.modalNuevo.set(false);
          this.avisos.ok(`Rol ${rol.nombre} creado. Ahora asignale sus permisos.`);
          this.cargar();
          this.abrir(rol);
        },
        error: (err) => {
          this.creando.set(false);
          this.errorNuevo.set(mensajeDeError(err, 'No se pudo crear el rol.'));
        },
      });
  }

  pedirBaja(rol: RolDetalle): void {
    this.errorEliminar.set(null);
    this.aEliminar.set(rol);
  }

  confirmarBaja(): void {
    const rol = this.aEliminar();
    if (!rol) return;
    this.eliminando.set(true);
    this.http.delete<{ detail: string }>(`${API_URL}/seguridad/roles/${rol.id}`).subscribe({
      next: (respuesta) => {
        this.eliminando.set(false);
        this.aEliminar.set(null);
        if (this.abierto()?.id === rol.id) this.cerrarEditor();
        this.avisos.ok(respuesta.detail);
        this.cargar();
      },
      error: (err) => {
        this.eliminando.set(false);
        this.errorEliminar.set(mensajeDeError(err, 'No se pudo eliminar el rol.'));
      },
    });
  }

  cerrarModales(): void {
    this.modalNuevo.set(false);
    this.aEliminar.set(null);
  }
}
