import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth.service';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { Notificaciones } from '../../../core/notificaciones';
import { contrasenaSegura, contrasenasIguales, ReglasContrasena } from '../../../shared/contrasena/reglas-contrasena';

const TELEFONO = /^[0-9+\-\s]{6,20}$/;

type Campo = 'nombre' | 'apellido' | 'email' | 'telefono' | 'password' | 'confirmar';

/**
 * CU20: registro de cliente. El backend crea el usuario con rol cliente y
 * devuelve la sesion, asi que al terminar ya puede reservar y comprar.
 */
@Component({
  selector: 'app-registro',
  imports: [ReactiveFormsModule, RouterLink, ReglasContrasena],
  templateUrl: './registro.html',
  styleUrls: ['../login/login.css', './registro.css'],
})
export class Registro {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private avisos = inject(Notificaciones);

  /** Solo rutas internas: evita que un enlace armado mande a otro sitio. */
  readonly volverA = (() => {
    const destino = inject(ActivatedRoute).snapshot.queryParamMap.get('volverA');
    return destino?.startsWith('/') && !destino.startsWith('//') ? destino : null;
  })();

  readonly enviando = signal(false);
  readonly error = signal<string | null>(null);
  readonly correoRepetido = signal(false);

  readonly formulario = this.fb.nonNullable.group(
    {
      nombre: ['', [Validators.required, Validators.maxLength(100), Validators.pattern(/\S/)]],
      apellido: ['', Validators.maxLength(100)],
      email: ['', [Validators.required, Validators.email, Validators.maxLength(120)]],
      telefono: ['', Validators.pattern(TELEFONO)],
      password: ['', [Validators.required, Validators.maxLength(72), contrasenaSegura]],
      confirmar: ['', Validators.required],
    },
    { validators: contrasenasIguales },
  );

  invalido(campo: Campo): boolean {
    const control = this.formulario.controls[campo];
    return control.invalid && (control.dirty || control.touched);
  }

  distintas(): boolean {
    const confirmar = this.formulario.controls.confirmar;
    return (confirmar.dirty || confirmar.touched) && this.formulario.hasError('distintas');
  }

  enviar(): void {
    this.error.set(null);
    this.correoRepetido.set(false);
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const crudo = this.formulario.getRawValue();
    const datos = {
      nombre: crudo.nombre.trim(),
      apellido: crudo.apellido.trim() || undefined,
      email: crudo.email.trim(),
      password: crudo.password,
      telefono: crudo.telefono.trim() || undefined,
    };

    // El boton queda deshabilitado mientras viaja: un doble clic no registra dos veces.
    this.enviando.set(true);
    this.auth.registrar(datos).subscribe({
      next: (sesion) => {
        this.enviando.set(false);
        this.avisos.ok(`Cuenta creada. Hola, ${sesion.usuario.nombre}: ya puedes reservar y comprar.`);
        this.router.navigateByUrl(this.volverA || '/catalogo');
      },
      error: (err) => {
        this.enviando.set(false);
        const mensaje = mensajeDeError(err, 'No se pudo crear la cuenta. Intenta de nuevo.');
        this.correoRepetido.set(err.status === 400 && /correo/i.test(mensaje));
        this.error.set(mensaje);
      },
    });
  }
}
