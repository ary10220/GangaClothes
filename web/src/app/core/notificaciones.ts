import { Injectable, signal } from '@angular/core';

export type TipoAviso = 'error' | 'ok';

export interface Aviso {
  id: number;
  tipo: TipoAviso;
  texto: string;
}

@Injectable({ providedIn: 'root' })
export class Notificaciones {
  private siguienteId = 1;
  readonly avisos = signal<Aviso[]>([]);

  error(texto: string): void {
    this.mostrar('error', texto);
  }

  ok(texto: string): void {
    this.mostrar('ok', texto);
  }

  cerrar(id: number): void {
    this.avisos.update((lista) => lista.filter((a) => a.id !== id));
  }

  private mostrar(tipo: TipoAviso, texto: string): void {
    const aviso: Aviso = { id: this.siguienteId++, tipo, texto };
    this.avisos.update((lista) => [...lista, aviso]);
    setTimeout(() => this.cerrar(aviso.id), 5000);
  }
}
