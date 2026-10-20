-- PLANET-005: the approved budget is unique per instant, append-only and bounded.
BEGIN;

INSERT INTO planet_quota_budget (
    period_start, period_end, max_area_m2, max_bytes, max_orders,
    approval_reference, approved_by, approved_at
) VALUES (
    timestamptz '2026-09-01 00:00:00+00', timestamptz '2026-10-01 00:00:00+00',
    30000.00, 314572800, 3, 'planet-budget-contract-test', 'data owner',
    timestamptz '2026-08-30 00:00:00+00'
);

-- Two budgets may never cover the same instant: the active budget must be unambiguous.
DO $$
BEGIN
    BEGIN
        INSERT INTO planet_quota_budget (
            period_start, period_end, max_area_m2, max_bytes, max_orders,
            approval_reference, approved_by, approved_at
        ) VALUES (
            timestamptz '2026-09-15 00:00:00+00', timestamptz '2026-10-15 00:00:00+00',
            10000.00, 104857600, 1, 'overlapping-budget', 'data owner',
            timestamptz '2026-09-14 00:00:00+00'
        );
        RAISE EXCEPTION 'an overlapping Planet quota budget was accepted';
    EXCEPTION
        WHEN exclusion_violation THEN NULL;
    END;
END;
$$;

-- An approved budget is evidence: it cannot be edited or removed in place.
DO $$
BEGIN
    BEGIN
        UPDATE planet_quota_budget SET max_orders = 99;
        RAISE EXCEPTION 'an approved Planet quota budget was updated';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'Planet quota budgets are append-only' THEN RAISE; END IF;
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        DELETE FROM planet_quota_budget;
        RAISE EXCEPTION 'an approved Planet quota budget was deleted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'Planet quota budgets are append-only' THEN RAISE; END IF;
    END;
END;
$$;

-- Limits must stay positive and the period ordered.
DO $$
BEGIN
    BEGIN
        INSERT INTO planet_quota_budget (
            period_start, period_end, max_area_m2, max_bytes, max_orders,
            approval_reference, approved_by, approved_at
        ) VALUES (
            timestamptz '2027-02-01 00:00:00+00', timestamptz '2027-01-01 00:00:00+00',
            1.00, 1, 1, 'inverted-period', 'data owner', timestamptz '2027-01-01 00:00:00+00'
        );
        RAISE EXCEPTION 'an inverted Planet quota period was accepted';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;
END;
$$;

ROLLBACK;
