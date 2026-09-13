/** Formatos de presentacion compartidos por las pantallas. */

/**
 * La base guarda las fechas en UTC y sin zona (`server_default=now()`), asi
 * que se interpretan como UTC y se muestran en la hora local del navegador.
 */
export function fechaLocal(iso: string | null | undefined): string {
  if (!iso) return '—';
  const conZona = /(z|[+-]\d{2}:\d{2})$/i.test(iso) ? iso : `${iso}Z`;
  const fecha = new Date(conZona);
  if (Number.isNaN(fecha.getTime())) return iso;
  return fecha.toLocaleString('es-BO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Fecha que el backend guarda tal como la eligio el usuario y sin zona, como
 * `fecha_hora_prueba` de una reserva: ya es hora local, se muestra sin convertir.
 */
export function fechaSinZona(iso: string | null | undefined): string {
  const fecha = instanteSinZona(iso);
  if (!fecha) return iso || '—';
  return fecha.toLocaleString('es-BO', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** El mismo valor de `fechaSinZona` como Date, para comparar con la hora actual. */
export function instanteSinZona(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const fecha = new Date(iso.replace(/(z|[+-]\d{2}:\d{2})$/i, ''));
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

/** Importe en bolivianos con punto de miles y coma decimal, como en el mockup: 1.234,50. */
export function moneda(valor: unknown): string {
  const numero = Number(valor ?? 0);
  return (Number.isFinite(numero) ? numero : 0).toLocaleString('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
