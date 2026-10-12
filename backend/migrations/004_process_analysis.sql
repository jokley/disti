-- Additive experimental analysis; canonical sensor_measurements is unchanged.
CREATE TABLE IF NOT EXISTS process_analysis (
  time timestamptz NOT NULL,
  vapor_temp double precision, dtdt double precision,
  raw_mv double precision, pt_raw_mv double precision,
  raw_mv_1m double precision, raw_mv_5m double precision,
  running_min_5m double precision, rise_from_min_5m double precision,
  trend_1m double precision, trend_3m double precision, trend_5m double precision,
  trend_accel_3m double precision, trend_accel_5m double precision,
  detector_name text NOT NULL, algo_version text NOT NULL,
  detector_score double precision NOT NULL, detector_alarm boolean NOT NULL,
  process_state text NOT NULL, ended boolean NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (time, detector_name, algo_version)
);
CREATE INDEX IF NOT EXISTS process_analysis_detector_time
  ON process_analysis(detector_name, algo_version, time DESC);
-- Existing sensor_measurements_sensor_time covers raw-data lookup;
-- no duplicate index or hypertable alteration.
