BEGIN;

DROP TRIGGER IF EXISTS authentication_session_revocation_immutable
    ON authentication_session_revocation;
DROP TRIGGER IF EXISTS authentication_session_immutable
    ON authentication_session;
DROP FUNCTION IF EXISTS prevent_authentication_session_audit_mutation();
DROP TABLE IF EXISTS authentication_session_revocation;
DROP TABLE IF EXISTS authentication_session;

COMMIT;
