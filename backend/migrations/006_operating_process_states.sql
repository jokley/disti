-- Old ENDE rows cannot be truthfully relabelled as BEREIT or ABKÜHLEN.
-- Invalidate only affected derived detector/version series. The unchanged live
-- worker restores them from sensor_measurements; raw data is never modified.
-- Conditional invalidation makes this safe for the existing repeatable runner.
DELETE FROM process_analysis
WHERE (detector_name, algo_version) IN (
  SELECT detector_name, algo_version FROM process_analysis
  WHERE process_state IN ('IDLE', 'ENDE', 'NACHLAUF_WAHRSCHEINLICH')
);
