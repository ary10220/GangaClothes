import { Component, computed, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { SesionStore } from '../../core/sesion';

/**
 * Barra superior de la tienda en linea: catalogo, compras, reservas y carrito del cliente.
 * Uso: `<app-barra-tienda />`.
 */
@Component({
  selector: 'app-barra-tienda',
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="topnav">
      <a class="logo" routerLink="/catalogo">Ganga<b>Clothes</b></a>
      <nav class="secciones">
        <a routerLink="/catalogo" routerLinkActive="on">Catalogo</a>
        @if (esCliente()) {
          <a routerLink="/mis-reservas" routerLinkActive="on">Mis reservas</a>
          <a routerLink="/mis-compras" routerLinkActive="on">Mis compras</a>
          <a routerLink="/mis-envios" routerLinkActive="on">Mis pedidos</a>
          <a routerLink="/carrito" routerLinkActive="on">Carrito</a>
        }
      </nav>

      @if (sesion.autenticado()) {
        <span class="yo">{{ sesion.nombreCompleto() }} · {{ sesion.rolPrincipal() }}</span>
        @if (esPersonal()) {
          <a class="btn linea acceso" routerLink="/admin">Ir al panel</a>
        }
        <button type="button" class="btn linea acceso" (click)="auth.salir()">Cerrar sesion</button>
      } @else {
        <a class="btn linea acceso invitado" routerLink="/login" [queryParams]="volver()">Iniciar sesion</a>
        <a class="btn rosa acceso" routerLink="/registro" [queryParams]="volver()">Crear cuenta</a>
      }
    </header>
  `,
  styles: `
    .topnav {
      display: flex;
      align-items: center;
      gap: 18px;
      flex-wrap: wrap;
      padding: 12px 26px;
      background: #fff;
      border-bottom: 1.5px solid var(--linea);
    }
    .logo {
      font-size: 17px;
    }
    .secciones {
      display: flex;
      gap: 16px;
    }
    .secciones a {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--gris);
      padding-bottom: 2px;
      border-bottom: 2px solid transparent;
    }
    .secciones a.on {
      color: var(--tinta);
      border-bottom-color: var(--ganga);
    }
    .yo {
      margin-left: auto;
      font-family: var(--mono);
      font-size: 10.5px;
      background: var(--suave);
      border: 1px solid var(--linea);
      border-radius: 99px;
      padding: 5px 13px;
      color: var(--gris);
    }
    .acceso {
      padding: 6px 13px;
      font-size: 11.5px;
    }
    .invitado {
      margin-left: auto;
    }
  `,
})
export class BarraTienda {
  readonly auth = inject(AuthService);
  readonly sesion = inject(SesionStore);
  private router = inject(Router);

  readonly esCliente = computed(() => this.sesion.tieneAlgunRol('cliente'));
  readonly esPersonal = computed(() => this.sesion.tieneAlgunRol('administrador', 'encargado', 'cajero'));

  /** Despues de entrar o registrarse, vuelve a la pagina donde estaba. */
  volver(): Record<string, string> {
    const url = this.router.url;
    return url.startsWith('/login') || url.startsWith('/registro') ? {} : { volverA: url };
  }
}
