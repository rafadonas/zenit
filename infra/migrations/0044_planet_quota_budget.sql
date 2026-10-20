BEGIN;

CREATE TABLE planet_quota_budget (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start timestamptz NOT NULL,
    period_end timestamptz NOT NULL,
    max_area_m2 numeric(14, 2) NOT NULL CHECK (max_area_m2 > 0),
    max_bytes bigint NOT NULL CHECK (max_bytes > 0),
    max_orders integer NOT NULL CHECK (max_orders > 0),
    approval_reference text NOT NULL CHECK (btrim(approval_reference) <> ''),
    approved_by text NOT NULL CHECK (btrim(approved_by) <> ''),
    approved_at timestamptz NOT NULL,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK (period_end > period_start),
    CHECK (approved_at <= period_end),
    EXCLUDE USING gist (tstzrange(period_start, period_end) WITH &&)
);

COMMENT ON TABLE planet_quota_budget IS
    'Approved Planet consumption budget per period; append-only, one budget per instant';

CREATE FUNCTION prevent_planet_quota_budget_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Planet quota budgets are append-only';
END;
$$;

CREATE TRIGGER planet_quota_budget_immutable
    BEFORE UPDATE OR DELETE ON planet_quota_budget
    FOR EACH ROW EXECUTE FUNCTION prevent_planet_quota_budget_mutation();

COMMIT;
