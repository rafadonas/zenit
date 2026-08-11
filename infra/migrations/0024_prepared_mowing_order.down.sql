BEGIN;
DROP TRIGGER IF EXISTS prepared_mowing_order_immutable ON prepared_mowing_order;
DROP TRIGGER IF EXISTS prepared_mowing_order_policy_immutable ON prepared_mowing_order_policy;
DROP FUNCTION IF EXISTS prevent_prepared_mowing_order_mutation();
DROP TRIGGER IF EXISTS prepared_mowing_order_guard ON prepared_mowing_order;
DROP FUNCTION IF EXISTS validate_prepared_mowing_order();
DROP TABLE IF EXISTS prepared_mowing_order;
DROP TABLE IF EXISTS prepared_mowing_order_policy;
COMMIT;
