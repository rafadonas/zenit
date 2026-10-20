BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM planet_quota_budget) THEN
        RAISE EXCEPTION 'cannot drop Planet quota budgets while approved budgets exist';
    END IF;
END;
$$;

DROP TRIGGER IF EXISTS planet_quota_budget_immutable ON planet_quota_budget;
DROP FUNCTION IF EXISTS prevent_planet_quota_budget_mutation();
DROP TABLE planet_quota_budget;

COMMIT;
