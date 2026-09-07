CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS sensors (
  id text PRIMARY KEY, name text NOT NULL, sensor_type text NOT NULL,
  bus text, address text, enabled boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS distillation_runs (
  id uuid PRIMARY KEY, run_type text NOT NULL CHECK (run_type IN ('gin','fruit brandy','other')),
  recipe_name text, batch_name text, notes text, status text NOT NULL DEFAULT 'active',
  started_at timestamptz NOT NULL, ended_at timestamptz
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_distillation_run ON distillation_runs(status) WHERE status='active';
CREATE TABLE IF NOT EXISTS sensor_calibrations (
  id uuid PRIMARY KEY, sensor_id text NOT NULL REFERENCES sensors(id), version text NOT NULL,
  model text NOT NULL DEFAULT 'linear', points jsonb NOT NULL DEFAULT '[]'::jsonb,
  slope double precision, offset double precision, active boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL, metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_calibration_per_sensor ON sensor_calibrations(sensor_id) WHERE active;
CREATE TABLE IF NOT EXISTS sensor_measurements (
  id uuid NOT NULL, time timestamptz NOT NULL, run_id uuid REFERENCES distillation_runs(id),
  sensor_id text NOT NULL REFERENCES sensors(id), measurement_type text NOT NULL,
  raw_value double precision, raw_mv double precision, value double precision NOT NULL, unit text NOT NULL,
  temperature double precision, calibration_id uuid REFERENCES sensor_calibrations(id),
  quality text NOT NULL DEFAULT 'good', metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (id, time)
);
SELECT create_hypertable('sensor_measurements', by_range('time'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS sensor_measurements_run_time ON sensor_measurements(run_id,time DESC);
CREATE INDEX IF NOT EXISTS sensor_measurements_sensor_time ON sensor_measurements(sensor_id,time DESC);
CREATE TABLE IF NOT EXISTS fractions (
  id uuid PRIMARY KEY, run_id uuid NOT NULL REFERENCES distillation_runs(id), fraction_number integer,
  fraction_type text, operator_notes text, started_at timestamptz NOT NULL, ended_at timestamptz
);
CREATE TABLE IF NOT EXISTS actuator_events (
  id uuid PRIMARY KEY, time timestamptz NOT NULL, run_id uuid REFERENCES distillation_runs(id),
  actuator_id text, event_type text NOT NULL, status text NOT NULL, details jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS hardware_events (
  id uuid PRIMARY KEY, time timestamptz NOT NULL DEFAULT now(), severity text NOT NULL,
  component text NOT NULL, event_type text NOT NULL, message text, details jsonb NOT NULL DEFAULT '{}'::jsonb
);
