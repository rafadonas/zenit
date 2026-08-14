BEGIN;

CREATE TABLE authentication_login_throttle (
    identifier_digest char(64) PRIMARY KEY
        CHECK (identifier_digest ~ '^[0-9a-f]{64}$'),
    failed_attempt_count integer NOT NULL CHECK (failed_attempt_count > 0),
    window_started_at timestamptz NOT NULL,
    blocked_until timestamptz,
    policy_version text NOT NULL CHECK (btrim(policy_version) <> ''),
    updated_at timestamptz NOT NULL,
    CHECK (blocked_until IS NULL OR blocked_until > window_started_at),
    CHECK (updated_at >= window_started_at)
);

CREATE INDEX authentication_login_throttle_blocked_idx
    ON authentication_login_throttle (blocked_until)
    WHERE blocked_until IS NOT NULL;

CREATE TABLE authentication_login_attempt (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier_digest char(64) NOT NULL
        CHECK (identifier_digest ~ '^[0-9a-f]{64}$'),
    outcome text NOT NULL CHECK (outcome IN ('succeeded', 'failed', 'blocked')),
    policy_version text NOT NULL CHECK (btrim(policy_version) <> ''),
    correlation_id uuid NOT NULL,
    occurred_at timestamptz NOT NULL
);

CREATE INDEX authentication_login_attempt_digest_idx
    ON authentication_login_attempt (identifier_digest, occurred_at DESC);
CREATE INDEX authentication_login_attempt_correlation_idx
    ON authentication_login_attempt (correlation_id);

CREATE FUNCTION prevent_authentication_login_attempt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'authentication login attempts are append-only';
END;
$$;

CREATE TRIGGER authentication_login_attempt_immutable
BEFORE UPDATE OR DELETE ON authentication_login_attempt
FOR EACH ROW EXECUTE FUNCTION prevent_authentication_login_attempt_mutation();

COMMIT;
