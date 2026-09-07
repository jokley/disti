-- Additive audit fields; existing calibration rows and measurement history remain intact.
ALTER TABLE sensor_calibrations ADD COLUMN IF NOT EXISTS finalized_at timestamptz;
ALTER TABLE sensor_calibrations ADD COLUMN IF NOT EXISTS activated_at timestamptz;
