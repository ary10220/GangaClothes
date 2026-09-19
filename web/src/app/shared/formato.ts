/** Formatos de presentacion compartidos por las pantallas. */

/**
 * UNICA funcion para mostrar un instante guardado por el sistema (bitacora,
 * movimientos, compras, ventas, pagos, reportes...). La API los manda en UTC
 * marcados con "Z"; aca se muestran en la hora de quien mira la pantalla, que
 * en Bolivia es UTC-4. Si llegara sin marca, se asume UTC igual.
 *
 * No usar para `reserva.fecha_hora_prueba`: esa es la hora de la tienda que
 * eligio el cliente y se muestra con `fechaSinZona`.
 */
export function instanteLocal(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const conZona = /(z|[+-]\d{2}:\d{2})$/i.test(iso) ? iso : `${iso}Z`;
  const fecha = new Date(conZona);
  return Number.isNaN(fecha.getTime()) ? null : fecha;
}

export function fechaLocal(iso: string | null | undefined): string {
  const fecha = instanteLocal(iso);
  if (!fecha) return iso || '—';
  return fecha.toLocaleString('es-BO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Solo el dia: "14/09" o "14/09/2026". Acepta un instante (se convierte a la
 * hora local) o una fecha suelta "2026-09-14", que ya es un dia y no se toca.
 */
export function fechaCortaLocal(iso: string | null | undefined, conAnio = false): string {
  if (!iso) return '—';
  if (iso.length <= 10) {
    const [a, m, d] = iso.slice(0, 10).split('-');
    return conAnio ? `${d}/${m}/${a}` : `${d}/${m}`;
  }
  const fecha = instanteLocal(iso);
  if (!fecha) return iso;
  return fecha.toLocaleDateString('es-BO', {
    day: '2-digit',
    month: '2-digit',
    ...(conAnio ? { year: 'numeric' } : {}),
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

/** Valor para un `<input type="datetime-local">` en hora local: "2026-09-14T15:00". */
export function paraCampoFechaHora(fecha: Date): string {
  const dos = (n: number) => String(n).padStart(2, '0');
  return (
    `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}` +
    `T${dos(fecha.getHours())}:${dos(fecha.getMinutes())}`
  );
}

/** Porcentaje con coma decimal y sin ceros de relleno: 42.98 -> "42,98%", 45.7 -> "45,7%". */
export function porcentaje(valor: unknown): string {
  const numero = Number(valor ?? 0);
  return `${(Number.isFinite(numero) ? numero : 0).toLocaleString('es-BO', { maximumFractionDigits: 2 })}%`;
}

/** Importe en bolivianos con punto de miles y coma decimal, como en el mockup: 1.234,50. */
export function moneda(valor: unknown): string {
  const numero = Number(valor ?? 0);
  return (Number.isFinite(numero) ? numero : 0).toLocaleString('es-BO', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}
