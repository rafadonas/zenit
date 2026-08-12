import 'dart:convert';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';

import 'measurement_draft.dart';
import 'prepared_work_order.dart';

enum MowingPhotoUploadState {
  notUploaded('not_uploaded'),
  uploadedUnverified('uploaded_unverified');

  const MowingPhotoUploadState(this.wireValue);
  final String wireValue;

  static MowingPhotoUploadState fromWire(String value) => values.firstWhere(
    (state) => state.wireValue == value,
    orElse: () => throw const FormatException(
      'Unknown mowing post-service photo upload state',
    ),
  );
}

class MowingPostServicePhotoDraft {
  const MowingPostServicePhotoDraft({
    required this.eventId,
    required this.photoId,
    required this.mowingOrderId,
    required this.sourcePlanningApprovalId,
    required this.sourcePlannedPointId,
    required this.sequence,
    required this.capturedAt,
    required this.checksumSha256,
    required this.mediaType,
    required this.bytes,
    this.syncState = DraftSyncState.localOnly,
    this.syncResultCode,
    this.syncResultMessage,
    this.uploadState = MowingPhotoUploadState.notUploaded,
  });

  final String eventId;
  final String photoId;
  final String mowingOrderId;
  final String sourcePlanningApprovalId;
  final String sourcePlannedPointId;
  final int sequence;
  final DateTime capturedAt;
  final String checksumSha256;
  final String mediaType;
  final Uint8List bytes;
  final DraftSyncState syncState;
  final String? syncResultCode;
  final String? syncResultMessage;
  final MowingPhotoUploadState uploadState;

  bool get hasPersistentServerResult =>
      syncState == DraftSyncState.acknowledged ||
      syncState == DraftSyncState.rejected ||
      syncState == DraftSyncState.conflict;

  bool get isUploaded =>
      uploadState == MowingPhotoUploadState.uploadedUnverified;

  bool get awaitsFutureUpload =>
      syncState == DraftSyncState.acknowledged && !isUploaded;

  MowingPostServicePhotoDraft copyWith({
    DraftSyncState? syncState,
    String? syncResultCode,
    String? syncResultMessage,
    bool clearResult = false,
    MowingPhotoUploadState? uploadState,
  }) => MowingPostServicePhotoDraft(
    eventId: eventId,
    photoId: photoId,
    mowingOrderId: mowingOrderId,
    sourcePlanningApprovalId: sourcePlanningApprovalId,
    sourcePlannedPointId: sourcePlannedPointId,
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
    uploadState: uploadState ?? this.uploadState,
  );

  JsonMap toSyncEventJson() {
    _validateValues();
    return {
      'event_id': eventId,
      'entity_type': 'mowing_photo',
      'operation': 'prepare',
      'payload': {
        'photo_id': photoId,
        'mowing_order_id': mowingOrderId,
        'source_planning_approval_id': sourcePlanningApprovalId,
        'source_planned_point_id': sourcePlannedPointId,
        'phase': 'post_service',
        'captured_at': capturedAt.toUtc().toIso8601String(),
        'checksum_sha256': checksumSha256,
        'byte_size': bytes.length,
        'media_type': mediaType,
        'photo_scope': 'mowing_demo_post_service_only',
        'content_status': 'not_uploaded',
        'ruler_status': 'not_validated',
        'location_status': 'not_collected',
        'data_status': 'simulated',
        'quality_status': 'simulated_unverified',
        'operational_approval_satisfied': false,
        'authorizes_field_work': false,
        'eligible_for_field_execution': false,
        'eligible_for_model_training': false,
        'eligible_for_official_reporting': false,
      },
    };
  }

  JsonMap toJson() {
    _validateValues();
    return {
      'event_id': eventId,
      'photo_id': photoId,
      'mowing_order_id': mowingOrderId,
      'source_planning_approval_id': sourcePlanningApprovalId,
      'source_planned_point_id': sourcePlannedPointId,
      'sequence': sequence,
      'captured_at': capturedAt.toUtc().toIso8601String(),
      'checksum_sha256': checksumSha256,
      'media_type': mediaType,
      'content_base64': base64Encode(bytes),
      'phase': 'post_service',
      'photo_scope': 'mowing_demo_post_service_only',
      'content_status': uploadState.wireValue,
      'ruler_status': 'not_validated',
      'location_status': 'not_collected',
      'data_status': 'simulated',
      'quality_status': 'simulated_unverified',
      'operational_approval_satisfied': false,
      'authorizes_field_work': false,
      'eligible_for_field_execution': false,
      'eligible_for_model_training': false,
      'eligible_for_official_reporting': false,
      'sync_state': syncState.wireValue,
      'sync_result_code': syncResultCode,
      'sync_result_message': syncResultMessage,
    };
  }

  factory MowingPostServicePhotoDraft.fromJson(JsonMap json) {
    final uploadState = MowingPhotoUploadState.fromWire(
      json['content_status']! as String,
    );
    final syncState = DraftSyncState.fromWire(json['sync_state']! as String);
    if (json['phase'] != 'post_service' ||
        json['photo_scope'] != 'mowing_demo_post_service_only' ||
        (uploadState == MowingPhotoUploadState.uploadedUnverified &&
            syncState != DraftSyncState.acknowledged) ||
        json['ruler_status'] != 'not_validated' ||
        json['location_status'] != 'not_collected' ||
        json['data_status'] != 'simulated' ||
        json['quality_status'] != 'simulated_unverified' ||
        json['operational_approval_satisfied'] != false ||
        json['authorizes_field_work'] != false ||
        json['eligible_for_field_execution'] != false ||
        json['eligible_for_model_training'] != false ||
        json['eligible_for_official_reporting'] != false) {
      throw const FormatException(
        'Mowing post-service photo crossed a safety boundary',
      );
    }
    final draft = MowingPostServicePhotoDraft(
      eventId: json['event_id']! as String,
      photoId: json['photo_id']! as String,
      mowingOrderId: json['mowing_order_id']! as String,
      sourcePlanningApprovalId: json['source_planning_approval_id']! as String,
      sourcePlannedPointId: json['source_planned_point_id']! as String,
      sequence: json['sequence']! as int,
      capturedAt: DateTime.parse(json['captured_at']! as String).toUtc(),
      checksumSha256: json['checksum_sha256']! as String,
      mediaType: json['media_type']! as String,
      bytes: base64Decode(json['content_base64']! as String),
      syncState: syncState,
      syncResultCode: json['sync_result_code'] as String?,
      syncResultMessage: json['sync_result_message'] as String?,
      uploadState: uploadState,
    );
    try {
      draft._validateValues();
    } on StateError catch (error) {
      throw FormatException(error.message);
    }
    return draft;
  }

  void _validateValues() {
    if (eventId.isEmpty ||
        photoId.isEmpty ||
        mowingOrderId.isEmpty ||
        sourcePlanningApprovalId.isEmpty ||
        sourcePlannedPointId.isEmpty ||
        sequence < 1 ||
        sequence > 3 ||
        bytes.isEmpty ||
        bytes.length > 26214400 ||
        !const {'image/jpeg', 'image/png'}.contains(mediaType) ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(checksumSha256) ||
        sha256.convert(bytes).toString() != checksumSha256) {
      throw StateError('Mowing post-service photo is invalid');
    }
  }
}
