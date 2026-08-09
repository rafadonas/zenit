import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:image_picker/image_picker.dart';

class CapturedPhoto {
  const CapturedPhoto({
    required this.bytes,
    required this.mediaType,
    required this.checksumSha256,
  });

  final Uint8List bytes;
  final String mediaType;
  final String checksumSha256;
}

abstract interface class PhotoCapture {
  Future<CapturedPhoto?> capture();
}

class ImagePickerPhotoCapture implements PhotoCapture {
  ImagePickerPhotoCapture({ImagePicker? picker})
    : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  @override
  Future<CapturedPhoto?> capture() async {
    final file = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 85,
      maxWidth: 2048,
    );
    if (file == null) return null;
    try {
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty || bytes.length > 26214400) {
        throw const FormatException('Photo must be between 1 byte and 25 MiB');
      }
      final mediaType = _detectMediaType(bytes);
      return CapturedPhoto(
        bytes: bytes,
        mediaType: mediaType,
        checksumSha256: sha256.convert(bytes).toString(),
      );
    } finally {
      try {
        final temporary = File(file.path);
        if (await temporary.exists()) await temporary.delete();
      } on FileSystemException {
        // The picker can return a non-file content URI. The OS owns its cleanup.
      }
    }
  }

  static String _detectMediaType(Uint8List bytes) {
    if (bytes.length >= 3 &&
        bytes[0] == 0xff &&
        bytes[1] == 0xd8 &&
        bytes[2] == 0xff) {
      return 'image/jpeg';
    }
    if (bytes.length >= 8 &&
        bytes[0] == 0x89 &&
        bytes[1] == 0x50 &&
        bytes[2] == 0x4e &&
        bytes[3] == 0x47 &&
        bytes[4] == 0x0d &&
        bytes[5] == 0x0a &&
        bytes[6] == 0x1a &&
        bytes[7] == 0x0a) {
      return 'image/png';
    }
    throw const FormatException('Only JPEG and PNG photos are accepted');
  }
}
