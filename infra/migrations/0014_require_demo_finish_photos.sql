BEGIN;

CREATE FUNCTION validate_prepared_demo_finish_photos()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.operation = 'finish' AND 3 <> (
        SELECT count(DISTINCT photo.planned_point_id)
        FROM prepared_field_photo_manifest photo
        WHERE photo.work_order_id = NEW.work_order_id
    ) THEN
        RAISE EXCEPTION 'finish requires three prepared point photo manifests';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prepared_demo_finish_photo_guard
BEFORE INSERT ON prepared_work_order_demo_event
FOR EACH ROW EXECUTE FUNCTION validate_prepared_demo_finish_photos();

COMMIT;
