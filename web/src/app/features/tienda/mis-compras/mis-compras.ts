import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { API_URL } from '../../../core/api';
import { mensajeDeError } from '../../../core/errores.interceptor';
import { fechaLocal, moneda } from '../../../shared/formato';
import { BarraTienda } from '../../../shared/tienda/barra-tienda';

interface DetalleCompra {
  id: number;
  sku: string;
  prenda: string;
  talla: string;
  color: string;
  cantidad: number;
  precio_unitario: number;
  subtotal: number;
}

interface PagoCompra {
  id: number;
  metodo: string;
  monto: number;
  estado: string;
  referencia_externa: string | null;
}

interface CompraCliente {
  id: number;
  estado: string;
  fecha: string | null;
  sucursal: string | null;
  unidades: number;
  subtotal: number;
  descuento: number;
  total: number;
  nro_comprobante: string | null;
  detalle: DetalleCompra[];
  pagos: PagoCompra[];
}

/** GET /api/ventas/mias: compras pagadas del cliente autenticado. */
@Component({
  selector: 'app-mis-compras',
  imports: [RouterLink, BarraTienda],
  templateUrl: './mis-compras.html',
  styleUrl: './mis-compras.css',
})
export class MisCompras {
  private http = inject(HttpClient);

  readonly fechaCompra = fechaLocal;
  readonly moneda = moneda;
  readonly compras = signal<CompraCliente[]>([]);
  readonly cargando = signal(true);
  readonly error = signal<string | null>(null);

  constructor() {
    this.cargar();
  }

  cargar(): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<CompraCliente[]>(`${API_URL}/ventas/mias`).subscribe({
      next: (compras) => {
        this.compras.set(compras);
        this.cargando.set(false);
      },
      error: (err) => {
        this.error.set(mensajeDeError(err, 'No se pudieron cargar tus compras.'));
        this.cargando.set(false);
      },
    });
  }

  pagoExitoso(compra: CompraCliente): PagoCompra | null {
    return compra.pagos.find((pago) => pago.estado === 'exitoso') ?? compra.pagos.at(-1) ?? null;
  }

  metodoPago(metodo: string | undefined): string {
    switch (metodo) {
      case 'pasarela':
        return 'Tarjeta / pasarela';
      case 'efectivo':
        return 'Efectivo';
      case 'tarjeta':
        return 'Tarjeta';
      case 'qr':
        return 'QR';
      default:
        return metodo || 'No informado';
    }
  }

  estadoPago(estado: string | undefined): string {
    return estado === 'exitoso' ? 'aprobado' : estado || 'No informado';
  }
}
