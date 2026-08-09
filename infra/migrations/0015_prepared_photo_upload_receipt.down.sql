BEGIN;

DROP TRIGGER IF EXISTS prepared_photo_upload_receipt_immutable
    ON prepared_photo_upload_receipt;
DROP TRIGGER IF EXISTS prepared_photo_upload_receipt_guard
    ON prepared_photo_upload_receipt;
DROP FUNCTION IF EXISTS validate_prepared_photo_upload_receipt();
DROP TABLE IF EXISTS prepared_photo_upload_receipt;

COMMIT;
