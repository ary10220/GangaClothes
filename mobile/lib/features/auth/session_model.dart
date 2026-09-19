class User {
  const User({
    required this.id,
    required this.name,
    this.lastName,
    required this.email,
    this.roles = const [],
    this.permissions = const [],
  });

  final int id;
  final String name;
  final String? lastName;
  final String email;
  final List<String> roles;
  final List<String> permissions;

  factory User.fromJson(Map<String, dynamic> json) {
    final id = _intValue(json['id']);
    final name = json['nombre'];
    final email = json['email'];
    if (id == null || name is! String || email is! String) {
      throw const FormatException('Invalid user session data');
    }

    return User(
      id: id,
      name: name,
      lastName: json['apellido'] as String?,
      email: email,
      roles: _stringList(json['roles']),
      permissions: _stringList(json['permisos']),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'nombre': name,
    if (lastName != null) 'apellido': lastName,
    'email': email,
    'roles': roles,
    'permisos': permissions,
  };

  String get fullName => [name, lastName].whereType<String>().join(' ');
}

class Session {
  const Session({
    required this.accessToken,
    required this.user,
    this.tokenType = 'bearer',
  });

  final String accessToken;
  final String tokenType;
  final User user;

  factory Session.fromJson(Map<String, dynamic> json) {
    final token = json['access_token'];
    final rawUser = json['usuario'];
    if (token is! String || token.trim().isEmpty || rawUser is! Map) {
      throw const FormatException('Invalid session data');
    }

    return Session(
      accessToken: token,
      tokenType: json['token_type'] as String? ?? 'bearer',
      user: User.fromJson(Map<String, dynamic>.from(rawUser)),
    );
  }

  Map<String, dynamic> toJson() => {
    'access_token': accessToken,
    'token_type': tokenType,
    'usuario': user.toJson(),
  };
}

int? _intValue(Object? value) {
  if (value is int) return value;
  return value is String ? int.tryParse(value) : null;
}

List<String> _stringList(Object? value) {
  if (value is! Iterable) return const [];
  return value.whereType<String>().toList(growable: false);
}
