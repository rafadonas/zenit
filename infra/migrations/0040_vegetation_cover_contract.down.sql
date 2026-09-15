BEGIN;

DROP TRIGGER IF EXISTS vegetation_cover_observation_immutable ON vegetation_cover_observation;
DROP FUNCTION IF EXISTS prevent_vegetation_cover_observation_mutation();
DROP TRIGGER IF EXISTS vegetation_cover_observation_chain_guard ON vegetation_cover_observation;
DROP FUNCTION IF EXISTS validate_vegetation_cover_observation_chain();
DROP TABLE IF EXISTS vegetation_cover_observation;

COMMIT;
