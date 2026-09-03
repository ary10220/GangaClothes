import { Component } from '@angular/core';

// Pantalla 10 de la iteracion 1. Por ahora es el destino de los clientes tras
// el login; se completa con /api/catalogo y sus filtros en el siguiente paso.
@Component({
  selector: 'app-catalogo',
  template: `
    <div class="marco">
      <div class="logo">Ganga<b>Clothes</b></div>
      <h1>Catalogo</h1>
      <p>Pantalla del cliente en construccion — consumira <code>GET /api/catalogo</code> con filtros.</p>
    </div>
  `,
  styles: `
    .marco {
      max-width: 720px;
      margin: 80px auto;
      padding: 0 20px;
    }
    .logo {
      font-size: 22px;
      margin-bottom: 18px;
    }
    h1 {
      font-size: 22px;
      font-weight: 800;
      letter-spacing: -0.02em;
    }
    p {
      color: var(--gris);
      font-size: 13px;
      margin-top: 8px;
    }
    code {
      font-family: var(--mono);
      font-size: 12px;
    }
  `,
})
export class Catalogo {}
