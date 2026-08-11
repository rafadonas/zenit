BEGIN;
DROP TRIGGER IF EXISTS prepared_mowing_resource_plan_immutable
    ON prepared_mowing_resource_plan;
DROP TRIGGER IF EXISTS prepared_mowing_resource_plan_policy_immutable
    ON prepared_mowing_resource_plan_policy;
DROP FUNCTION IF EXISTS prevent_prepared_mowing_resource_plan_mutation();
DROP TRIGGER IF EXISTS prepared_mowing_resource_plan_guard
    ON prepared_mowing_resource_plan;
DROP FUNCTION IF EXISTS validate_prepared_mowing_resource_plan();
DROP TABLE IF EXISTS prepared_mowing_resource_plan;
DROP TABLE IF EXISTS prepared_mowing_resource_plan_policy;
COMMIT;
