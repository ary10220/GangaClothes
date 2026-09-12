import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { Registro } from '../../../core/recurso.service';
import { SesionStore } from '../../../core/sesion';
import { esInactivo, filtrarPorEstado, FiltroEstado, textoPie, textoVacio } from '../../../shared/estado/estado';
import { SelectorEstado } from '../../../shared/estado/selector-estado';

/**
 * Administrar usuarios y roles. No usa la fabrica generica porque los roles
 * son una lista, la contrasena solo se manda al crear, el correo no se puede
 * editar y no hay DELETE: el usuario se archiva con `activo`.
 */
@Component({
  selector: 'app-usuarios',
  imports: [ReactiveFormsModule, SelectorEstado],
  templateUrl: './usuarios.html',
  styleUrl: './usuarios.css',
  host: { '(document:keydown.escape)': 'cerrarModal()' },
})
export class Usuarios {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);
  private avisos = inject(Notificaciones);
  private sesion = inject(SesionStore);

  /** Los roles se traen de la API: si se crea uno nuevo, aparece aca solo. */
  readonly roles = signal<string[]>([]);

  // ---- listado ----
  readonly usuarios = signal<Registro[]>([]);
  readonly cargando = signal(true);
  readonly errorCarga = signal<string | null>(null);
  readonly busqueda = signal('');
  readonly estado = signal<FiltroEstado>('activos');

  // ---- formulario ----
  readonly modalAbierto = signal(false);
  readonly editando = signal<Registro | null>(null);
  readonly guardando = signal(false);
  readonly errorFormulario = signal<string | null>(null);
  /** Los roles se manejan aparte del FormGroup porque son chips, no un control. */
  readonly rolesElegidos = signal<string[]>([]);
  readonly errorRoles = signal(false);
  formulario: FormGroup = this.fb.group({});

  readonly cambiandoEstado = signal<number | null>(null);

  readonly enEstado = computed(() => filtrarPorEstado(this.usuarios(), this.estado()));

  readonly visibles = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    if (!texto) return this.enEstado();
    return this.enEstado().filter((u) =>
      [u['nombre'], u['apellido'], u['email'], (u['roles'] as string[])?.join(' ')]
        .join(' ')
        .toLowerCase()
        .includes(texto),
    );
  });

  readonly archivados = computed(() => this.usuarios().filter((u) => esInactivo(u)).length);
  readonly muestraEstado = computed(() => this.estado() === 'todos');
  readonly pie = computed(() => textoPie(this.visibles().length, this.enEstado().length, this.estado(), true));
  readonly mensajeVacio = computed(() =>
    textoVacio(this.usuarios().length, this.archivados(), this.estado(), 'usuarios'),
  );

  constructor() {
    this.cargarRoles();
    this.cargar();
  }

  private cargarRoles(): void {
    this.http.get<{ nombre: string; activo: boolean }[]>(`${API_URL}/seguridad/roles`).subscribe({
      next: (filas) => this.roles.set(filas.filter((r) => r.activo).map((r) => r.nombre)),
      error: () => this.avisos.error('No se pudieron cargar los roles disponibles.'),
    });
  }

  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set(null);
    this.http.get<Registro[]>(`${API_URL}/usuarios`).subscribe({
      next: (filas) => {
        this.usuarios.set(filas);
        this.cargando.set(false);
      },
      error: (err) => {
        this.errorCarga.set(mensajeDeError(err, 'No se pudieron cargar los usuarios.'));
        this.cargando.set(false);
      },
    });
  }

  // ------------------------------------------------------------- formulario
  abrirNuevo(): void {
    this.editando.set(null);
    this.errorFormulario.set(null);
    this.errorRoles.set(false);
    this.rolesElegidos.set(['cliente']);
    this.formulario = this.fb.group({
      nombre: ['', Validators.required],
      apellido: [''],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      telefono: [''],
    });
    this.modalAbierto.set(true);
  }

  abrirEdicion(usuario: Registro): void {
    this.editando.set(usuario);
    this.errorFormulario.set(null);
    this.errorRoles.set(false);
    this.rolesElegidos.set([...((usuario['roles'] as string[]) ?? [])]);
    const texto = (clave: string) =>
      usuario[clave] === null || usuario[clave] === undefined ? '' : String(usuario[clave]);
    // Al editar, el correo se muestra pero no se toca: el backend no lo actualiza.
    this.formulario = this.fb.group({
      nombre: [texto('nombre'), Validators.required],
      apellido: [texto('apellido')],
      telefono: [texto('telefono')],
    });
    this.modalAbierto.set(true);
  }

  invalido(campo: string): boolean {
    const control = this.formulario.get(campo);
    return !!control && control.invalid && (control.dirty || control.touched);
  }

  alternarRol(rol: string): void {
    this.rolesElegidos.update((actuales) =>
      actuales.includes(rol) ? actuales.filter((r) => r !== rol) : [...actuales, rol],
    );
    if (this.rolesElegidos().length > 0) this.errorRoles.set(false);
  }

  tieneRol(rol: string): boolean {
    return this.rolesElegidos().includes(rol);
  }

  guardar(): void {
    // Sin rol el usuario entraria al sistema sin poder hacer nada.
    if (this.rolesElegidos().length === 0) this.errorRoles.set(true);
    if (this.formulario.invalid) this.formulario.markAllAsTouched();
    if (this.formulario.invalid || this.rolesElegidos().length === 0) return;

    this.errorFormulario.set(null);
    this.guardando.set(true);

    const crudo = this.formulario.getRawValue();
    const usuario = this.editando();

    const peticion = usuario
      ? this.http.put<Registro>(`${API_URL}/usuarios/${usuario.id}`, {
          nombre: crudo.nombre,
          apellido: crudo.apellido || null,
          telefono: crudo.telefono || null,
          roles: this.rolesElegidos(),
        })
      : this.http.post<Registro>(`${API_URL}/usuarios`, {
          nombre: crudo.nombre,
          apellido: crudo.apellido || null,
          email: crudo.email,
          password: crudo.password,
          telefono: crudo.telefono || null,
          roles: this.rolesElegidos(),
        });

    peticion.subscribe({
      next: () => {
        this.guardando.set(false);
        this.modalAbierto.set(false);
        this.avisos.ok(usuario ? 'Se actualizo el usuario.' : 'Se creo el usuario.');
        this.cargar();
      },
      error: (err) => {
        this.guardando.set(false);
        this.errorFormulario.set(mensajeDeError(err, 'No se pudo guardar el usuario.'));
      },
    });
  }

  /** No hay DELETE de usuarios: se archiva y se reactiva con `activo`. */
  cambiarEstado(usuario: Registro, activo: boolean): void {
    this.cambiandoEstado.set(usuario.id);
    this.http.put<Registro>(`${API_URL}/usuarios/${usuario.id}`, { activo }).subscribe({
      next: () => {
        this.cambiandoEstado.set(null);
        this.avisos.ok(activo ? 'Se reactivo el usuario.' : 'Se archivo el usuario.');
        this.cargar();
      },
      error: (err) => {
        this.cambiandoEstado.set(null);
        this.avisos.error(mensajeDeError(err, 'No se pudo cambiar el estado del usuario.'));
      },
    });
  }

  cerrarModal(): void {
    this.modalAbierto.set(false);
  }

  // ------------------------------------------------------------ presentacion
  esInactivo(usuario: Registro): boolean {
    return esInactivo(usuario);
  }

  rolesDe(usuario: Registro): string[] {
    return (usuario['roles'] as string[]) ?? [];
  }

  nombreCompleto(usuario: Registro): string {
    return [usuario['nombre'], usuario['apellido']].filter(Boolean).join(' ');
  }

  /** Nadie deberia poder archivar su propia cuenta y quedarse afuera. */
  esMiCuenta(usuario: Registro): boolean {
    return this.sesion.usuario()?.id === usuario.id;
  }
}
