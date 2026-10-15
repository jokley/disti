-- Invalidate complete affected derived series so the unchanged worker can
-- reconstruct physical states across quality gaps from sensor_measurements.
-- Relabelling quality states cannot recover the preceding process state.
-- Conditional and repeatable; no raw measurements are changed.
DELETE FROM process_analysis
WHERE (detector_name, algo_version) IN (
  SELECT detector_name, algo_version FROM process_analysis
  WHERE process_state IN (
    'BEREIT', 'ABKÜHLEN', 'ENDE', 'SENSOR_UNGUELTIG', 'DATENLUECKE',
    'IDLE', 'NACHLAUF_WAHRSCHEINLICH'
  )
);
