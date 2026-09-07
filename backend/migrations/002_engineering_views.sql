-- Grafana-ready first and second derivatives. Raw observations remain immutable.
CREATE OR REPLACE VIEW measurement_derivatives AS
WITH first_derivative AS (
  SELECT time, run_id, sensor_id, measurement_type, value, raw_value, raw_mv,
    temperature, quality,
    (value - lag(value) OVER series) /
      NULLIF(EXTRACT(epoch FROM time - lag(time) OVER series), 0) AS value_rate
  FROM sensor_measurements
  WINDOW series AS (PARTITION BY run_id, sensor_id, measurement_type ORDER BY time)
)
SELECT *,
  (value_rate - lag(value_rate) OVER series) /
    NULLIF(EXTRACT(epoch FROM time - lag(time) OVER series), 0) AS value_acceleration
FROM first_derivative
WINDOW series AS (PARTITION BY run_id, sensor_id, measurement_type ORDER BY time);

CREATE OR REPLACE VIEW distillation_timeline AS
SELECT time, run_id, 'measurement' AS marker_type, sensor_id AS source,
       jsonb_build_object('type',measurement_type,'value',value,'unit',unit) AS details
FROM sensor_measurements
UNION ALL
SELECT started_at, run_id, 'fraction_start', id::text,
       jsonb_build_object('number',fraction_number,'type',fraction_type) FROM fractions
UNION ALL
SELECT time, run_id, event_type, COALESCE(actuator_id,id::text), details FROM actuator_events;
