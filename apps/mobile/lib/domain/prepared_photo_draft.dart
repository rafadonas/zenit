import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

import 'measurement_draft.dart';

class PreparedPhotoDraft {
  const PreparedPhotoDraft({
    required this.eventId,
    required this.photoId,
    required this.orderId,
    required this.plannedPointId,
    required this.sequence,
    required this.capturedAt,
    required this.checksumSha256,
    required this.mediaType,
    required this.bytes,
    this.syncState = DraftSyncState.localOnly,
    this.syncResultCode,
    this.syncResultMessage,
  });

  final String eventId;
  final String photoId;
  final String orderId;
  final String plannedPointId;
  final int sequence;
  final DateTime capturedAt;
  final String checksumSha256;
  final String mediaType;
  final Uint8List bytes;
  final DraftSyncState syncState;
  final String? syncResultCode;
  final String? syncResultMessage;

  bool get hasPersistentServerResult =>
      syncState == DraftSyncState.acknowledged ||
      syncState == DraftSyncState.rejected ||
      syncState == DraftSyncState.conflict;

  PreparedPhotoDraft copyWith({
    DraftSyncState? syncState,
    String? syncResultCode,
    String? syncResultMessage,
    bool clearResult = false,
  }) => PreparedPhotoDraft(
    eventId: eventId,
    photoId: photoId,
    orderId: orderId,
    plannedPointId: plannedPointId,
    sequence: sequence,
    capturedAt: capturedAt,
    checksumSha256: checksumSha256,
    mediaType: mediaType,
    bytes: bytes,
    syncState: syncState ?? this.syncState,
    syncResultCode: clearResult ? null : syncResultCode ?? this.syncResultCode,
    syncResultMessage: clearResult
        ? null
        : syncResultMessage ?? this.syncResultMessage,
  );

  Map<String, Object?> toSyncEventJson() => {
    'event_id': eventId,
    'entity_type': 'photo',
    'operation': 'prepare',
    'payload': {
      'photo_id': photoId,
      'work_order_id': orderId,
      'planned_point_id': plannedPointId,
      'phase': 'inspection',
      'captured_at': capturedAt.toUtc().toIso8601String(),
      'checksum_sha256': checksumSha256,
      'byte_size': bytes.length,
      'media_type': mediaType,
      'content_status': 'not_uploaded',
      'ruler_status': 'not_validated',
      'location_status': 'not_collected',
      'data_status': 'prepared',
      'eligible_for_official_reporting': false,
    },
  };

  Map<String, Object?> toJson() => {
    'event_id': eventId,
    'photo_id': photoId,
    'order_id': orderId,
    'planned_point_id': plannedPointId,
    'sequence': sequence,
    'captured_at': capturedAt.toUtc().toIso8601String(),
    'checksum_sha256': checksumSha256,
    'media_type': mediaType,
    'content_base64': base64Encode(bytes),
    'content_status': 'not_uploaded',
    'ruler_status': 'not_validated',
    'data_status': 'prepared',
    'eligible_for_official_reporting': false,
    'sync_state': syncState.wireValue,
    'sync_result_code': syncResultCode,
    'sync_result_message': syncResultMessage,
  };

  factory PreparedPhotoDraft.fromJson(Map<String, Object?> json) {
    if (json['content_status'] != 'not_uploaded' ||
        json['ruler_status'] != 'not_validated' ||
        json['data_status'] != 'prepared' ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException('Photo draft crossed a safety boundary');
    }
    final bytes = base64Decode(json['content_base64']! as String);
    final checksum = json['checksum_sha256']! as String;
    if (bytes.isEmpty ||
        bytes.length > 26214400 ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(checksum) ||
        sha256.convert(bytes).toString() != checksum) {
      throw const FormatException('Photo draft content metadata is invalid');
    }
    return PreparedPhotoDraft(
      eventId: json['event_id']! as String,
      photoId: json['photo_id']! as String,
      orderId: json['order_id']! as String,
      plannedPointId: json['planned_point_id']! as String,
      sequence: json['sequence']! as int,
      capturedAt: DateTime.parse(json['captured_at']! as String).toUtc(),
      checksumSha256: checksum,
      mediaType: json['media_type']! as String,
      bytes: bytes,
      syncState: DraftSyncState.fromWire(json['sync_state']! as String),
      syncResultCode: json['sync_result_code'] as String?,
      syncResultMessage: json['sync_result_message'] as String?,
    );
  }
}
