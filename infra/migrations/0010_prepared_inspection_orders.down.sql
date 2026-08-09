BEGIN;

DROP TRIGGER IF EXISTS work_order_planned_point_immutable ON work_order_planned_point;
DROP TRIGGER IF EXISTS work_order_immutable ON work_order;
DROP TRIGGER IF EXISTS inspection_order_policy_immutable ON inspection_order_policy;
DROP FUNCTION IF EXISTS prevent_prepared_inspection_order_mutation();
DROP TRIGGER IF EXISTS work_order_point_count_guard ON work_order;
DROP FUNCTION IF EXISTS validate_work_order_point_count();
DROP TRIGGER IF EXISTS work_order_planned_point_guard ON work_order_planned_point;
DROP FUNCTION IF EXISTS validate_work_order_planned_point();
DROP TRIGGER IF EXISTS prepared_inspection_order_guard ON work_order;
DROP FUNCTION IF EXISTS validate_prepared_inspection_order();
DROP TABLE IF EXISTS work_order_planned_point;
DROP TABLE IF EXISTS work_order;
DROP TABLE IF EXISTS inspection_order_policy;

COMMIT;
