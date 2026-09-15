BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM planet_order) OR EXISTS (SELECT 1 FROM planet_order_event) THEN
        RAISE EXCEPTION 'cannot downgrade while Planet Order evidence exists';
    END IF;
END
$$;

DROP TRIGGER IF EXISTS planet_order_event_immutable ON planet_order_event;
DROP FUNCTION IF EXISTS prevent_planet_order_event_mutation();
DROP TABLE IF EXISTS planet_order_event;
ALTER TABLE satellite_asset DROP COLUMN IF EXISTS source_order_id;
DROP INDEX IF EXISTS planet_order_state_idx;
DROP TABLE IF EXISTS planet_order;

COMMIT;
