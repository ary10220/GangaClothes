import { Component, input } from '@angular/core';
import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export interface ReglaContrasena {
  texto: string;
  cumple: (valor: string) => boolean;
}

/** Misma regla que el backend (core/contrasenas.py) para toda contrasena nueva. */
export const REGLAS_CONTRASENA: ReglaContrasena[] = [
  { texto: 'Al menos 8 caracteres', cumple: (v) => v.length >= 8 },
  { texto: 'Una mayuscula', cumple: (v) => /[A-ZÁÉÍÓÚÜÑ]/.test(v) },
  { texto: 'Una minuscula', cumple: (v) => /[a-záéíóúüñ]/.test(v) },
  { texto: 'Un numero', cumple: (v) => /\d/.test(v) },
  { texto: 'Un caracter especial (! @ # $ % & * . - _)', cumple: (v) => /[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\s]/.test(v) },
];

/** El campo vacio lo marca `Validators.required`; aca solo se revisa la regla. */
export const contrasenaSegura: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const valor = String(control.value ?? '');
  if (!valor) return null;
  return REGLAS_CONTRASENA.every((r) => r.cumple(valor)) ? null : { insegura: true };
};

/** Validador de grupo: `password` y `confirmar` tienen que ser iguales. */
export function contrasenasIguales(grupo: AbstractControl): ValidationErrors | null {
  const password = grupo.get('password')?.value;
  const confirmar = grupo.get('confirmar')?.value;
  return password && confirmar && password !== confirmar ? { distintas: true } : null;
}

/**
 * Lista de requisitos que se va marcando mientras se escribe.
 * Uso: `<app-reglas-contrasena [valor]="form.controls.password.value" />`.
 */
@Component({
  selector: 'app-reglas-contrasena',
  template: `
    <ul class="reglas" aria-label="Requisitos de la contrasena">
      @for (regla of reglas; track regla.texto) {
        <li [class.cumple]="regla.cumple(valor())">
          <span class="marca" aria-hidden="true">{{ regla.cumple(valor()) ? '✓' : '○' }}</span>
          {{ regla.texto }}
          <span class="oculto">{{ regla.cumple(valor()) ? '(cumple)' : '(falta)' }}</span>
        </li>
      }
    </ul>
  `,
  styles: `
    .reglas {
      list-style: none;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 3px 12px;
      font-size: 11.5px;
      color: var(--gris);
      margin: 2px 0 12px;
    }
    li.cumple {
      color: var(--ok);
    }
    /* El del caracter especial lleva ejemplos: ocupa la fila entera. */
    li:last-child {
      grid-column: 1 / -1;
    }
    .marca {
      display: inline-block;
      width: 14px;
      font-weight: 700;
    }
    .oculto {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
    }
    @media (max-width: 480px) {
      .reglas {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class ReglasContrasena {
  readonly valor = input<string>('');
  readonly reglas = REGLAS_CONTRASENA;
}
