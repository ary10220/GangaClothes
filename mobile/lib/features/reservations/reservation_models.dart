abstract final class ReservationStatus {
  static const pending = 'pendiente';
  static const prepared = 'preparada';
  static const attended = 'atendida';
  static const cancelled = 'cancelada';
  static const expired = 'expirada';

  static const all = <String>[pending, prepared, attended, cancelled, expired];

  static const active = <String>[pending, prepared];

  static bool isActive(String status) => active.contains(status);

  static String explanation(String status) => switch (status) {
    pending => 'La sucursal recibio tu reserva y va a preparar las prendas.',
    prepared => 'Tus prendas te esperan en el vestidor.',
    attended => 'Ya pasaste por la tienda a probartelas.',
    cancelled =>
      'Cancelaste esta reserva; las prendas volvieron a estar disponibles.',
    expired => 'No llegaste a la cita y las prendas se liberaron.',
    _ => 'El estado de tu reserva se actualizo.',
  };
}

class ReservationDetail {
  const ReservationDetail({
    required this.id,
    required this.variantId,
    required this.sku,
    required this.garment,
    required this.size,
    required this.color,
    required this.quantity,
    this.status,
  });

  final int id;
  final int variantId;
  final String sku;
  final String garment;
  final String size;
  final String color;
  final int quantity;
  final String? status;

  factory ReservationDetail.fromJson(Map<String, dynamic> json) =>
      ReservationDetail(
        id: _intValue(json['id']),
        variantId: _intValue(json['variante_id']),
        sku: _stringValue(json['sku']),
        garment: _stringValue(json['prenda']),
        size: _stringValue(json['talla']),
        color: _stringValue(json['color']),
        quantity: _intValue(json['cantidad']),
        status: _nullableString(json['estado']),
      );
}

class Reservation {
  const Reservation({
    required this.id,
    required this.status,
    required this.createdAtRaw,
    required this.appointmentRaw,
    required this.notes,
    required this.branch,
    required this.units,
    required this.details,
  });

  final int id;
  final String status;
  final String? createdAtRaw;
  final String appointmentRaw;
  final String? notes;
  final String branch;
  final int units;
  final List<ReservationDetail> details;

  bool get isActive => ReservationStatus.isActive(status);

  DateTime? get appointmentAt => parseLocalAppointment(appointmentRaw);

  DateTime? get createdAt => parseCreationTimestamp(createdAtRaw);

  factory Reservation.fromJson(Map<String, dynamic> json) => Reservation(
    id: _intValue(json['id']),
    status: _stringValue(json['estado']),
    createdAtRaw: _nullableString(json['fecha_creacion']),
    appointmentRaw: _stringValue(json['fecha_hora_prueba']),
    notes: _nullableString(json['notas'])?.trim().isEmpty == true
        ? null
        : _nullableString(json['notas'])?.trim(),
    branch: _stringValue(json['sucursal']),
    units: _intValue(json['unidades']),
    details: _details(json['detalle']),
  );
}

DateTime? parseLocalAppointment(String? value) {
  if (value == null || value.trim().isEmpty) return null;
  // The appointment is a local store time. Strip a defensive suffix instead
  // of allowing a timezone conversion to move the displayed appointment.
  final localValue = value.replaceFirst(RegExp(r'(z|[+-]\d{2}:\d{2})$'), '');
  return DateTime.tryParse(localValue);
}

DateTime? parseCreationTimestamp(String? value) {
  if (value == null || value.trim().isEmpty) return null;
  final hasZone = RegExp(
    r'(z|[+-]\d{2}:\d{2})$',
    caseSensitive: false,
  ).hasMatch(value);
  final parsed = DateTime.tryParse(hasZone ? value : '${value}Z');
  return parsed?.toLocal();
}

String formatAppointment(String? value) {
  final date = parseLocalAppointment(value);
  if (date == null) return value?.trim().isNotEmpty == true ? value! : '—';
  return '${_weekday[date.weekday - 1]}, ${_twoDigits(date.day)}/'
      '${_twoDigits(date.month)}, ${_twoDigits(date.hour)}:${_twoDigits(date.minute)}';
}

String formatCreation(String? value) {
  final date = parseCreationTimestamp(value);
  if (date == null) return value?.trim().isNotEmpty == true ? value! : '—';
  return '${_twoDigits(date.day)}/${_twoDigits(date.month)}/${date.year} '
      '${_twoDigits(date.hour)}:${_twoDigits(date.minute)}';
}

bool isOverdueActive(Reservation reservation, {DateTime? now}) {
  final appointment = reservation.appointmentAt;
  return reservation.isActive &&
      appointment != null &&
      appointment.isBefore(now ?? DateTime.now());
}

const _weekday = <String>['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'];

String _twoDigits(int value) => value.toString().padLeft(2, '0');

int _intValue(Object? value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse('$value') ?? 0;
}

String _stringValue(Object? value) => value is String ? value : '$value';

String? _nullableString(Object? value) => value is String ? value : null;

List<ReservationDetail> _details(Object? value) {
  if (value is! List) return const [];
  return value
      .whereType<Map>()
      .map(
        (item) => ReservationDetail.fromJson(Map<String, dynamic>.from(item)),
      )
      .toList(growable: false);
}
