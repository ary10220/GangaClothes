import { Component, inject, isDevMode, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../../core/auth.service';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { CUENTAS_DEMO, CuentaDemo } from '../../../../environments/cuentas-demo';

/**
 * Los atajos de cuentas solo tienen sentido corriendo en local. Hay dos
 * barreras: esta condicion oculta el bloque, y el `fileReplacements` de
 * angular.json deja la lista vacia en la compilacion de produccion, para que
 * las credenciales ni siquiera existan dentro del bundle publicado.
 */
function enLocal(): boolean {
  return isDevMode() || ['localhost', '127.0.0.1', '[::1]'].includes(location.hostname);
}

@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);
  private ruta = inject(ActivatedRoute);

  readonly mostrarCuentasDemo = enLocal() && CUENTAS_DEMO.length > 0;
  readonly cuentasDemo = CUENTAS_DEMO;
  readonly enviando = signal(false);
  readonly error = signal<string | null>(null);

  readonly formulario = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  usar(cuenta: CuentaDemo): void {
    this.formulario.setValue({ email: cuenta.email, password: cuenta.password });
  }

  invalido(campo: 'email' | 'password'): boolean {
    const control = this.formulario.controls[campo];
    return control.invalid && (control.dirty || control.touched);
  }

  enviar(): void {
    this.error.set(null);
    if (this.formulario.invalid) {
      this.formulario.markAllAsTouched();
      return;
    }

    const { email, password } = this.formulario.getRawValue();
    this.enviando.set(true);
    this.auth.login(email, password).subscribe({
      next: () => {
        this.enviando.set(false);
        const volverA = this.ruta.snapshot.queryParamMap.get('volverA');
        this.router.navigateByUrl(volverA || this.auth.rutaInicial());
      },
      error: (err) => {
        this.enviando.set(false);
        this.error.set(
          err.status === 401
            ? 'Correo o contrasena incorrectos.'
            : mensajeDeError(err, 'No se pudo iniciar sesion. Intenta de nuevo.'),
        );
      },
    });
  }
}
