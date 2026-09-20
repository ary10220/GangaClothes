import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { API_URL } from '../core/api';
import { mensajeDeError } from '../core/errores.interceptor';
import { Notificaciones } from '../core/notificaciones';

/**
 * Comprobante de venta en PDF (CU15), para la caja y para la tienda en linea.
 *
 * El PDF no se puede abrir con un `<a href>` porque la ruta pide el token: hay
 * que traerlo con HttpClient (el interceptor agrega la cabecera) y recien
 * entonces mostrarlo. Eso obliga a dos cuidados:
 *
 *  - la pestana se abre ANTES de pedir el archivo. Si se abriera al recibirlo,
 *    el navegador lo tomaria como una ventana emergente y la bloquearia;
 *  - la URL temporal se libera despues, o cada impresion deja memoria ocupada.
 */
@Injectable({ providedIn: 'root' })
export class Comprobantes {
  private http = inject(HttpClient);
  private avisos = inject(Notificaciones);

  /** Abre el PDF en una pestana nueva, con el visor del navegador listo para imprimir. */
  imprimir(ventaId: number): void {
    const pestana = window.open('', '_blank');
    this.pedir(ventaId, false).then(
      (blob) => {
        const url = URL.createObjectURL(blob);
        if (pestana) {
          pestana.location.href = url;
          // El visor tarda en montarse; liberar antes dejaria la pestana en blanco.
          setTimeout(() => URL.revokeObjectURL(url), 60_000);
        } else {
          // Si el navegador bloqueo la pestana, al menos que se lo lleve descargado.
          this.guardar(url, `comprobante-venta-${ventaId}.pdf`);
          this.avisos.ok('Tu navegador bloqueo la ventana: el comprobante se descargo.');
        }
      },
      (err) => {
        pestana?.close();
        this.avisos.error(mensajeDeError(err, 'No se pudo abrir el comprobante.'));
      },
    );
  }

  /** Descarga el PDF como archivo. */
  descargar(ventaId: number, nroComprobante?: string | null): void {
    this.pedir(ventaId, true).then(
      (blob) => {
        const url = URL.createObjectURL(blob);
        this.guardar(url, `comprobante-${nroComprobante ?? `venta-${ventaId}`}.pdf`);
        URL.revokeObjectURL(url);
      },
      (err) => this.avisos.error(mensajeDeError(err, 'No se pudo descargar el comprobante.')),
    );
  }

  private pedir(ventaId: number, descargar: boolean): Promise<Blob> {
    const url = `${API_URL}/ventas/${ventaId}/comprobante.pdf${descargar ? '?descargar=true' : ''}`;
    return new Promise((resolver, rechazar) => {
      this.http.get(url, { responseType: 'blob' }).subscribe({ next: resolver, error: rechazar });
    });
  }

  private guardar(url: string, nombre: string): void {
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombre;
    enlace.click();
  }
}
