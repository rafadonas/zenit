BEGIN;

DROP TABLE IF EXISTS data_lineage;
DROP TABLE IF EXISTS staging_vegetation_observation;
DROP TABLE IF EXISTS staging_mowing_polygon;
DROP TABLE IF EXISTS staging_km_marker;
DROP TABLE IF EXISTS import_anomaly;
DROP TABLE IF EXISTS import_run;
DROP TABLE IF EXISTS import_job;
DROP TABLE IF EXISTS source_file;

COMMIT;
