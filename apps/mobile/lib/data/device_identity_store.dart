import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract interface class DeviceIdentityStore {
  Future<String> readOrCreate();
  Future<void> clear();
}

class SecureDeviceIdentityStore implements DeviceIdentityStore {
  SecureDeviceIdentityStore([FlutterSecureStorage? storage])
    : _storage = storage ?? const FlutterSecureStorage();

  static const _deviceIdKey = 'zenit.mobile.device-id.v1';
  final FlutterSecureStorage _storage;

  @override
  Future<String> readOrCreate() async {
    final existing = await _storage.read(key: _deviceIdKey);
    if (existing != null) return existing;
    final created = generateUuidV4();
    await _storage.write(key: _deviceIdKey, value: created);
    return created;
  }

  @override
  Future<void> clear() => _storage.delete(key: _deviceIdKey);
}

String generateUuidV4([Random? random]) {
  final source = random ?? Random.secure();
  final bytes = List<int>.generate(16, (_) => source.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  final hex = bytes
      .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
      .join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-'
      '${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}
