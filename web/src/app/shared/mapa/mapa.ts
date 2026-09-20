import {
  AfterViewInit,
  Component,
  DestroyRef,
  ElementRef,
  effect,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import * as L from 'leaflet';

/** Un punto en el mapa. El `tipo` decide como se dibuja el marcador. */
export interface PuntoMapa {
  latitud: number;
  longitud: number;
  /** origen = la sucursal que despacha · destino = a donde va · pendiente = otro pedido de la lista. */
  tipo: 'origen' | 'destino' | 'pendiente';
  titulo?: string;
  detalle?: string;
}

export interface Coordenada {
  latitud: number;
  longitud: number;
}

/** Santa Cruz de la Sierra: el centro por defecto cuando todavia no hay puntos. */
const CENTRO_POR_DEFECTO: L.LatLngTuple = [-17.7833, -63.1821];

/**
 * Mapa Leaflet con tiles de OpenStreetMap.
 *
 *   <app-mapa [puntos]="puntos()" [unirPuntos]="true" />
 *   <app-mapa [seleccionable]="true" (elegido)="marcar($event)" />
 *
 * OpenStreetMap es gratis y no pide clave ni tarjeta; a cambio exige mostrar su
 * atribucion, que va en el pie del mapa (`attribution` de la capa).
 *
 * Los marcadores son `divIcon`, es decir HTML y CSS, y no las imagenes que trae
 * Leaflet: asi no hay que copiar PNG al build ni pelear con las rutas que el
 * empaquetador les cambia, y ademas quedan con los colores de la tienda.
 */
@Component({
  selector: 'app-mapa',
  template: `
    <div class="marco" [style.height]="alto()">
      <div class="lienzo" #lienzo></div>
      @if (seleccionable()) {
        <p class="pista">{{ pista() }}</p>
      }
    </div>
  `,
  styles: `
    .marco {
      position: relative;
      border: 1.5px solid var(--linea);
      border-radius: 13px;
      overflow: hidden;
      background: #e8e8e0;
    }
    .lienzo {
      width: 100%;
      height: 100%;
    }
    .pista {
      position: absolute;
      left: 10px;
      right: 10px;
      bottom: 10px;
      z-index: 500;
      margin: 0;
      padding: 7px 11px;
      border-radius: 9px;
      background: rgba(20, 22, 26, 0.82);
      color: #fff;
      font-size: 11.5px;
      text-align: center;
      pointer-events: none;
    }
    /* Los marcadores son HTML: se les da forma aca. */
    :host ::ng-deep .gc-pin {
      display: grid;
      place-items: center;
      width: 26px;
      height: 26px;
      border-radius: 50% 50% 50% 4px;
      transform: rotate(-45deg);
      border: 2px solid #fff;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
      font-size: 12px;
      font-weight: 700;
      color: #fff;
    }
    :host ::ng-deep .gc-pin span {
      transform: rotate(45deg);
    }
    :host ::ng-deep .gc-pin.origen {
      background: var(--tinta);
    }
    :host ::ng-deep .gc-pin.destino {
      background: var(--ganga);
    }
    :host ::ng-deep .gc-pin.pendiente {
      background: var(--alerta);
    }
    :host ::ng-deep .leaflet-container {
      font-family: var(--sans);
    }
    :host ::ng-deep .leaflet-popup-content {
      margin: 10px 12px;
      font-size: 12.5px;
      line-height: 1.45;
    }
  `,
})
export class Mapa implements AfterViewInit {
  private readonly lienzo = viewChild.required<ElementRef<HTMLElement>>('lienzo');

  readonly puntos = input<PuntoMapa[]>([]);
  /** Permite marcar la ubicacion tocando el mapa (checkout del cliente). */
  readonly seleccionable = input(false);
  /** Dibuja la linea entre el origen y el destino (seguimiento del pedido). */
  readonly unirPuntos = input(false);
  readonly alto = input('320px');
  readonly zoom = input(13);
  readonly pista = input('Toca el mapa para marcar donde quieres recibir tu compra');

  readonly elegido = output<Coordenada>();

  /** Se guarda en un campo: `inject` solo se puede llamar al construir. */
  private readonly destruccion = inject(DestroyRef);

  private mapa: L.Map | null = null;
  private capa: L.LayerGroup | null = null;
  /** Cambia cuando el mapa ya existe, para que el effect vuelva a dibujar. */
  private readonly listo = signal(false);
  /** Ultimo encuadre hecho; evita reencuadrar en cada redibujo (ver `dibujar`). */
  private encuadre = '';

  constructor() {
    effect(() => {
      const puntos = this.puntos();
      if (this.listo()) this.dibujar(puntos);
    });
    this.destruccion.onDestroy(() => {
      // `stop()` corta la animacion de zoom o desplazamiento que pudiera estar
      // corriendo: si el mapa se destruye en medio de una, Leaflet intenta
      // leer la posicion de un panel que ya no existe y tira un error.
      this.mapa?.stop();
      this.mapa?.remove();
      this.mapa = null;
    });
  }

  ngAfterViewInit(): void {
    this.mapa = L.map(this.lienzo().nativeElement, {
      center: CENTRO_POR_DEFECTO,
      zoom: this.zoom(),
      // El scroll de la rueda se lo queda la pagina: en un carrito largo,
      // pasar por encima del mapa no deberia cambiarle el zoom sin querer.
      scrollWheelZoom: false,
    });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(this.mapa);
    this.capa = L.layerGroup().addTo(this.mapa);

    if (this.seleccionable()) {
      this.mapa.on('click', (evento: L.LeafletMouseEvent) =>
        this.elegido.emit({ latitud: evento.latlng.lat, longitud: evento.latlng.lng }),
      );
    }

    // El mapa se mide al crearse; si nacio dentro de un modal o de una tarjeta
    // que todavia no tenia su tamano final, queda con los tiles cortados.
    const observador = new ResizeObserver(() => this.mapa?.invalidateSize());
    observador.observe(this.lienzo().nativeElement);
    this.destruccion.onDestroy(() => observador.disconnect());

    this.listo.set(true);
    this.dibujar(this.puntos());
  }

  /** Centra el mapa en un punto sin esperar a que cambien los marcadores. */
  centrarEn(latitud: number, longitud: number, zoom = 16): void {
    this.mapa?.setView([latitud, longitud], zoom);
  }

  private dibujar(puntos: PuntoMapa[]): void {
    if (!this.mapa || !this.capa) return;
    this.capa.clearLayers();
    if (puntos.length === 0) {
      this.mapa.setView(CENTRO_POR_DEFECTO, this.zoom(), { animate: false });
      return;
    }

    for (const punto of puntos) {
      const marcador = L.marker([punto.latitud, punto.longitud], { icon: this.icono(punto.tipo) });
      if (punto.titulo || punto.detalle) {
        marcador.bindPopup(
          `<b>${escapar(punto.titulo ?? '')}</b>` +
            (punto.detalle ? `<br><span>${escapar(punto.detalle)}</span>` : ''),
        );
      }
      marcador.addTo(this.capa);
    }

    const origen = puntos.find((p) => p.tipo === 'origen');
    const destino = puntos.find((p) => p.tipo === 'destino');
    if (this.unirPuntos() && origen && destino) {
      L.polyline(
        [
          [origen.latitud, origen.longitud],
          [destino.latitud, destino.longitud],
        ],
        { color: '#e8175d', weight: 3, opacity: 0.8, dashArray: '7 7' },
      ).addTo(this.capa);
    }

    // El encuadre se rehace solo cuando cambia el conjunto SIN contar el
    // destino: mientras el cliente arrastra su punto por el mapa, la vista se
    // queda quieta en lugar de saltar en cada clic.
    const firma = [puntos.length, ...puntos.filter((p) => p.tipo !== 'destino')
      .map((p) => `${p.latitud.toFixed(4)},${p.longitud.toFixed(4)}`)].join('|');
    if (firma !== this.encuadre) {
      this.encuadre = firma;
      // Sin animacion: el encuadre cambia cuando cambian los datos, no cuando
      // el usuario mueve el mapa, y ver la vista "volar" ahi despista mas de lo
      // que ayuda (ademas de evitar animaciones a medio terminar).
      if (puntos.length === 1) {
        this.mapa.setView([puntos[0].latitud, puntos[0].longitud], 15, { animate: false });
      } else {
        const limites = L.latLngBounds(puntos.map((p) => [p.latitud, p.longitud] as L.LatLngTuple));
        this.mapa.fitBounds(limites, { padding: [36, 36], maxZoom: 16, animate: false });
      }
    }
    // Los tiles se piden con el tamano que el contenedor tenga en este momento.
    setTimeout(() => this.mapa?.invalidateSize(), 0);
  }

  private icono(tipo: PuntoMapa['tipo']): L.DivIcon {
    const letra = tipo === 'origen' ? 'T' : tipo === 'destino' ? 'D' : '!';
    return L.divIcon({
      className: '',
      html: `<div class="gc-pin ${tipo}"><span>${letra}</span></div>`,
      iconSize: [26, 26],
      iconAnchor: [13, 26],
      popupAnchor: [0, -24],
    });
  }
}

/** El texto de un popup se inserta como HTML: hay que escaparlo. */
function escapar(texto: string): string {
  return texto.replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c] ?? c,
  );
}
