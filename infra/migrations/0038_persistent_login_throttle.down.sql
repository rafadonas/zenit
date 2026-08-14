BEGIN;

DROP TRIGGER IF EXISTS authentication_login_attempt_immutable
    ON authentication_login_attempt;
DROP FUNCTION IF EXISTS prevent_authentication_login_attempt_mutation();
DROP TABLE IF EXISTS authentication_login_attempt;
DROP TABLE IF EXISTS authentication_login_throttle;

COMMIT;
