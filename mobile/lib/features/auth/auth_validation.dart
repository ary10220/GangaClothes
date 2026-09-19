import 'dart:convert';

class PasswordRule {
  const PasswordRule({required this.label, required this.matches});

  final String label;
  final bool Function(String value) matches;
}

/// These rules intentionally mirror both the Angular helper and the backend.
final passwordRules = <PasswordRule>[
  PasswordRule(
    label: 'Al menos 8 caracteres',
    matches: (value) => value.length >= 8,
  ),
  PasswordRule(
    label: 'Una mayúscula',
    matches: (value) => RegExp(r'[A-ZÁÉÍÓÚÜÑ]').hasMatch(value),
  ),
  PasswordRule(
    label: 'Una minúscula',
    matches: (value) => RegExp(r'[a-záéíóúüñ]').hasMatch(value),
  ),
  PasswordRule(
    label: 'Un número',
    matches: (value) => RegExp(r'\d').hasMatch(value),
  ),
  PasswordRule(
    label: 'Un carácter especial (! @ # \$ % & * . - _)',
    matches: (value) => RegExp(r'[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\s]').hasMatch(value),
  ),
];

bool isValidEmail(String value) {
  final email = value.trim();
  return email.length <= 120 &&
      RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email);
}

bool isValidLoginPassword(String value) => value.length >= 6;

bool isStrongPassword(String value) =>
    passwordRules.every((rule) => rule.matches(value)) &&
    utf8.encode(value).length <= 72;

bool isValidName(String value) {
  final name = value.trim();
  return name.isNotEmpty && name.length <= 100;
}

bool isValidPhone(String value) =>
    value.trim().isEmpty ||
    RegExp(r'^[0-9+\-\s]{6,20}$').hasMatch(value.trim());

String? passwordError(String value) {
  if (value.isEmpty) return 'La contraseña es obligatoria.';
  if (utf8.encode(value).length > 72) {
    return 'La contraseña no puede superar 72 bytes.';
  }
  final missing = passwordRules
      .where((rule) => !rule.matches(value))
      .map((rule) => rule.label.toLowerCase())
      .toList();
  if (missing.isEmpty) return null;
  return 'Cumple los requisitos de abajo.';
}
