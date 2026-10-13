-- Additive plateau-relative diagnostics; raw sensor data is unchanged.
ALTER TABLE process_analysis ADD COLUMN IF NOT EXISTS ec_plateau_ref double precision;
ALTER TABLE process_analysis ADD COLUMN IF NOT EXISTS ec_drop_from_plateau double precision;
ALTER TABLE process_analysis ADD COLUMN IF NOT EXISTS ec_min_since_plateau double precision;
ALTER TABLE process_analysis ADD COLUMN IF NOT EXISTS ec_recovery_from_min double precision;
