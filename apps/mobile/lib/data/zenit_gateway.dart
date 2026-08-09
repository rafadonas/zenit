import 'dart:convert';

import 'package:http/http.dart' as http;

import '../domain/auth_session.dart';
import '../domain/measurement_draft.dart';
import '../domain/mobile_sync.dart';
import '../domain/prepared_work_order.dart';

abstract interface class ZenitGateway {
  Future<AuthSession> login(String email, String password);
  Future<List<PreparedWorkOrder>> listPreparedOrders(String accessToken);
  Future<void> registerDevice(
    String accessToken,
    String deviceId,
    String appVersion,
  );
  Future<MobileSyncResult> syncBatch(
    String accessToken,
    PendingSyncBatch batch,
    List<MeasurementDraft> drafts,
  );
}

class ZenitApiException implements Exception {
  const ZenitApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class HttpZenitGateway implements ZenitGateway {
  HttpZenitGateway({
    required String baseUrl,
    http.Client? client,
    DateTime Function()? clock,
  }) : _baseUri = Uri.parse(baseUrl),
       _client = client ?? http.Client(),
       _clock = clock ?? DateTime.now;

  final Uri _baseUri;
  final http.Client _client;
  final DateTime Function() _clock;

  Uri _uri(String path, [Map<String, String>? query]) =>
      _baseUri.resolve(path).replace(queryParameters: query);

  @override
  Future<AuthSession> login(String email, String password) async {
    final response = await _client.post(
      _uri('/v1/auth/token'),
      headers: const {'Accept': 'application/json'},
      body: {'username': email.trim(), 'password': password},
    );
    final payload = _decodeObject(response);
    if (response.statusCode != 200) {
      throw ZenitApiException(
        _detail(payload, 'Falha na autenticação.'),
        statusCode: response.statusCode,
      );
    }
    final user = (payload['user']! as Map).cast<String, Object?>();
    return AuthSession(
      accessToken: payload['access_token']! as String,
      expiresAt: _clock().toUtc().add(
        Duration(seconds: payload['expires_in']! as int),
      ),
      userId: user['id']! as String,
      email: user['email']! as String,
      displayName: user['display_name']! as String,
    );
  }

  @override
  Future<List<PreparedWorkOrder>> listPreparedOrders(String accessToken) async {
    final response = await _client.get(
      _uri('/v1/work-orders', const {'limit': '100'}),
      headers: {
        'Accept': 'application/json',
        'Authorization': 'Bearer $accessToken',
      },
    );
    final payload = _decodeObject(response);
    if (response.statusCode != 200) {
      throw ZenitApiException(
        _detail(payload, 'Não foi possível baixar as ordens preparadas.'),
        statusCode: response.statusCode,
      );
    }
    final items = payload['items']! as List<Object?>;
    return items
        .map(
          (item) => PreparedWorkOrder.fromJson(
            (item! as Map).cast<String, Object?>(),
          ),
        )
        .toList(growable: false);
  }

  @override
  Future<void> registerDevice(
    String accessToken,
    String deviceId,
    String appVersion,
  ) async {
    final response = await _client.post(
      _uri('/v1/mobile/devices'),
      headers: _authorizedHeaders(accessToken),
      body: jsonEncode({
        'device_id': deviceId,
        'platform': 'android',
        'app_version': appVersion,
      }),
    );
    final payload = _decodeObject(response);
    if (response.statusCode != 200) {
      throw ZenitApiException(
        _detail(payload, 'Não foi possível registrar o dispositivo.'),
        statusCode: response.statusCode,
      );
    }
    if (payload['device_id'] != deviceId ||
        payload['registration_status'] != 'active' ||
        payload['data_status'] != 'prepared' ||
        payload['authorizes_field_work'] != false) {
      throw const ZenitApiException(
        'A API retornou um registro de dispositivo incompatível.',
      );
    }
  }

  @override
  Future<MobileSyncResult> syncBatch(
    String accessToken,
    PendingSyncBatch batch,
    List<MeasurementDraft> drafts,
  ) async {
    final response = await _client.post(
      _uri('/v1/sync/batch'),
      headers: _authorizedHeaders(accessToken),
      body: jsonEncode(batch.toRequestJson(drafts)),
    );
    final payload = _decodeObject(response);
    if (response.statusCode != 200) {
      throw ZenitApiException(
        _detail(payload, 'Não foi possível sincronizar o lote preparado.'),
        statusCode: response.statusCode,
      );
    }
    final result = MobileSyncResult.fromJson(payload);
    if (result.batchId != batch.batchId) {
      throw const ZenitApiException(
        'A API confirmou um lote diferente do enviado.',
      );
    }
    return result;
  }

  static Map<String, String> _authorizedHeaders(String accessToken) => {
    'Accept': 'application/json',
    'Authorization': 'Bearer $accessToken',
    'Content-Type': 'application/json',
  };

  static Map<String, Object?> _decodeObject(http.Response response) {
    try {
      return (jsonDecode(response.body) as Map).cast<String, Object?>();
    } on Object {
      throw ZenitApiException(
        'A API retornou uma resposta inválida.',
        statusCode: response.statusCode,
      );
    }
  }

  static String _detail(Map<String, Object?> payload, String fallback) {
    final detail = payload['detail'];
    return detail is String && detail.isNotEmpty ? detail : fallback;
  }
}
