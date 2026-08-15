BEGIN;

CREATE TABLE authentication_session (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES app_user(id),
    token_issuer text NOT NULL CHECK (btrim(token_issuer) <> ''),
    token_audience text NOT NULL CHECK (btrim(token_audience) <> ''),
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    correlation_id uuid NOT NULL,
    UNIQUE (id, user_id),
    CHECK (expires_at > issued_at)
);

CREATE INDEX authentication_session_user_expiry_idx
    ON authentication_session (user_id, expires_at DESC);
CREATE INDEX authentication_session_expiry_idx
    ON authentication_session (expires_at);
CREATE INDEX authentication_session_correlation_idx
    ON authentication_session (correlation_id);

CREATE TABLE authentication_session_revocation (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL UNIQUE,
    revoked_by_user_id uuid NOT NULL REFERENCES app_user(id),
    reason text NOT NULL CHECK (reason IN ('user_logout')),
    correlation_id uuid NOT NULL,
    revoked_at timestamptz NOT NULL,
    FOREIGN KEY (session_id, revoked_by_user_id)
        REFERENCES authentication_session(id, user_id)
);

CREATE INDEX authentication_session_revocation_actor_idx
    ON authentication_session_revocation (revoked_by_user_id, revoked_at DESC);
CREATE INDEX authentication_session_revocation_correlation_idx
    ON authentication_session_revocation (correlation_id);

CREATE FUNCTION prevent_authentication_session_audit_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'authentication session records are append-only';
END;
$$;

CREATE TRIGGER authentication_session_immutable
BEFORE UPDATE OR DELETE ON authentication_session
FOR EACH ROW EXECUTE FUNCTION prevent_authentication_session_audit_mutation();

CREATE TRIGGER authentication_session_revocation_immutable
BEFORE UPDATE OR DELETE ON authentication_session_revocation
FOR EACH ROW EXECUTE FUNCTION prevent_authentication_session_audit_mutation();

COMMIT;
