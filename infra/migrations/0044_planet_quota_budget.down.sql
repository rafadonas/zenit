BEGIN;

-- Reverting drops approved budgets, which are approval evidence. It requires an
-- explicit confirmation in the same session, so it can never happen by accident:
--   psql -c "SET zenit.confirm_destructive = 'planet_quota_budget'" \
--        -f infra/migrations/0044_planet_quota_budget.down.sql
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM planet_quota_budget)
       AND coalesce(current_setting('zenit.confirm_destructive', true), '')
           <> 'planet_quota_budget'
    THEN
        RAISE EXCEPTION
            'cannot drop Planet quota budgets while approved budgets exist; '
            'set zenit.confirm_destructive to planet_quota_budget to confirm';
    END IF;
END;
$$;

DROP TRIGGER IF EXISTS planet_quota_budget_immutable ON planet_quota_budget;
DROP FUNCTION IF EXISTS prevent_planet_quota_budget_mutation();
DROP TABLE planet_quota_budget;

COMMIT;
