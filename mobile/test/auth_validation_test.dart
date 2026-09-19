import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/features/auth/auth_validation.dart';

void main() {
  test('matches all five backend password rules', () {
    expect(passwordRules.map((rule) => rule.matches('Abcdef1!')).toList(), [
      true,
      true,
      true,
      true,
      true,
    ]);
    expect(passwordRules.map((rule) => rule.matches('abcdef1!')).toList(), [
      true,
      false,
      true,
      true,
      true,
    ]);
    expect(passwordRules.map((rule) => rule.matches('ABCDEF1!')).toList(), [
      true,
      true,
      false,
      true,
      true,
    ]);
    expect(passwordRules.map((rule) => rule.matches('Abcdefgh!')).toList(), [
      true,
      true,
      true,
      false,
      true,
    ]);
    expect(passwordRules.map((rule) => rule.matches('Abcdefg1')).toList(), [
      true,
      true,
      true,
      true,
      false,
    ]);
    expect(isStrongPassword('Abcdef1!'), isTrue);
  });

  test(
    'validates email, name, login password, phone, and confirmation inputs',
    () {
      expect(isValidEmail('user@example.com'), isTrue);
      expect(isValidEmail('not-an-email'), isFalse);
      expect(isValidName(' Ada '), isTrue);
      expect(isValidName('   '), isFalse);
      expect(isValidLoginPassword('12345'), isFalse);
      expect(isValidLoginPassword('123456'), isTrue);
      expect(isValidPhone('70012345'), isTrue);
      expect(isValidPhone('bad phone!'), isFalse);
      expect(passwordError('Abcdef1!'), isNull);
      expect(passwordError('Abcdef1'), isNotNull);
    },
  );
}
