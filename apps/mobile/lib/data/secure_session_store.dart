import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../domain/auth_session.dart';

abstract interface class SessionStore {
  Future<AuthSession?> readValid(DateTime now);
  Future<void> write(AuthSession session);
  Future<void> clear();
}

class SecureSessionStore implements SessionStore {
  SecureSessionStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  static const _sessionKey = 'zenit.auth.session.v1';
  final FlutterSecureStorage _storage;

  @override
  Future<AuthSession?> readValid(DateTime now) async {
    final encoded = await _storage.read(key: _sessionKey);
    if (encoded == null) return null;
    try {
      final session = AuthSession.fromJson(
        (jsonDecode(encoded) as Map).cast<String, Object?>(),
      );
      if (session.isValidAt(now)) return session;
    } on Object {
      // Corrupt or obsolete session material is removed below.
    }
    await clear();
    return null;
  }

  @override
  Future<void> write(AuthSession session) =>
      _storage.write(key: _sessionKey, value: jsonEncode(session.toJson()));

  @override
  Future<void> clear() => _storage.delete(key: _sessionKey);
}
