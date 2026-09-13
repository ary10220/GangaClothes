import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth.service';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { contrasenaSegura, contrasenasIguales, ReglasContrasena } from '../../../shared/contrasena/reglas-contrasena';

/**
 * Recuperar contrasena en dos pasos: el correo recibe un codigo de 6 digitos
 * y con ese codigo se crea una contrasena nueva (que cumple la misma regla que
 * el registro). Al terminar vuelve al login con el correo ya escrito.
 */
@Component({
  selector: 'app-recuperar',
  imports: [ReactiveFormsModule, RouterLink, ReglasContrasena],
  templateUrl: './recuperar.html',
  styleUrls: ['../login/login.css', './recuperar.css'],
})
export class Recuperar {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private avisos = inject(Notificaciones);

  readonly paso = signal<'correo' | 'codigo'>('correo');
  readonly enviando = signal(false);
  readonly error = signal<string | null>(null);
  readonly aviso = signal<string | null>(null);
  readonly minutos = signal(15);
  /** Segundos que faltan para poder pedir otro codigo. */
  readonly espera = signal(0);
  private reloj?: ReturnType<typeof setInterval>;

  readonly formCorreo = this.fb.nonNullable.group({
    email: [
      inject(ActivatedRoute).snapshot.queryParamMap.get('email') ?? '',
      [Validators.required, Validators.email, Validators.maxLength(120)],
    ],
  });

  readonly formCodigo = this.fb.nonNullable.group(
    {
      codigo: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
      password: ['', [Validators.required, Validators.maxLength(72), contrasenaSegura]],
      confirmar: ['', Validators.required],
    },
    { validators: contrasenasIguales },
  );

  constructor() {
    inject(DestroyRef).onDestroy(() => clearInterval(this.reloj));
  }

  get correo(): string {
    return this.formCorreo.controls.email.value.trim();
  }

  invalidoCorreo(): boolean {
    const c = this.formCorreo.controls.email;
    return c.invalid && (c.dirty || c.touched);
  }

  invalido(campo: 'codigo' | 'password' | 'confirmar'): boolean {
    const c = this.formCodigo.controls[campo];
    return c.invalid && (c.dirty || c.touched);
  }

  distintas(): boolean {
    const c = this.formCodigo.controls.confirmar;
    return (c.dirty || c.touched) && this.formCodigo.hasError('distintas');
  }

  // --------------------------------------------------------- paso 1: correo
  pedirCodigo(reenvio = false): void {
    this.error.set(null);
    if (this.formCorreo.invalid) {
      this.formCorreo.markAllAsTouched();
      return;
    }
    if (this.enviando() || (reenvio && this.espera() > 0)) return;

    this.enviando.set(true);
    this.auth.recuperar(this.correo).subscribe({
      next: (r) => {
        this.enviando.set(false);
        this.minutos.set(r.minutos ?? 15);
        this.iniciarEspera(r.reenvio_en ?? 60);
        this.paso.set('codigo');
        this.formCodigo.controls.codigo.reset('');
        this.aviso.set(
          reenvio
            ? `Te enviamos un codigo nuevo a ${this.correo}. El anterior ya no sirve.`
            : `Si ${this.correo} tiene una cuenta, te llego un codigo de 6 digitos.`,
        );
      },
      error: (err) => {
        this.enviando.set(false);
        this.error.set(mensajeDeError(err, 'No se pudo enviar el codigo. Intenta de nuevo.'));
      },
    });
  }

  usarOtroCorreo(): void {
    this.paso.set('correo');
    this.error.set(null);
    this.aviso.set(null);
  }

  // ------------------------------------------------- paso 2: codigo y clave
  restablecer(): void {
    this.error.set(null);
    if (this.formCodigo.invalid) {
      this.formCodigo.markAllAsTouched();
      return;
    }
    const { codigo, password } = this.formCodigo.getRawValue();
    this.enviando.set(true);
    this.auth.restablecer({ email: this.correo, codigo, password }).subscribe({
      next: () => {
        this.enviando.set(false);
        this.avisos.ok('Tu contrasena se actualizo. Inicia sesion con la nueva.');
        this.router.navigate(['/login'], { queryParams: { email: this.correo } });
      },
      error: (err) => {
        this.enviando.set(false);
        this.error.set(mensajeDeError(err, 'No se pudo cambiar la contrasena. Intenta de nuevo.'));
      },
    });
  }

  private iniciarEspera(segundos: number): void {
    clearInterval(this.reloj);
    this.espera.set(segundos);
    this.reloj = setInterval(() => {
      this.espera.update((s) => Math.max(0, s - 1));
      if (this.espera() === 0) clearInterval(this.reloj);
    }, 1000);
  }
}
