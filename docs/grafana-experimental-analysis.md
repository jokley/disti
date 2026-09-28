# Grafana: experimentelle Prozessanalyse

Der Bereich **Analyse / Experimental** ist eine rein lesende Arbeitshypothese für
die ersten Rohbrände. Er klassifiziert keine Prozessphasen, definiert keine
Schwellen und hat keinen Einfluss auf die Steuerung. Alle Werte werden bei jeder
Abfrage aus `sensor_measurements` berechnet und nicht persistiert.

## Feste Analyse-Semantik

Die Glättung ist der arithmetische Mittelwert aller Messungen eines Sensors in
einem an der Uhr ausgerichteten TimescaleDB-Bucket von exakt einer Minute:

```sql
time_bucket(INTERVAL '1 minute', time), avg(value)
```

`dT/dt` und `dEC/dt` vergleichen den Mittelwert mit `lag()` über den
vorhergehenden Bucket. Eine Ableitung wird nur ausgegeben, wenn die beiden
Bucket-Zeitstempel genau 60 Sekunden auseinanderliegen. Sie wird als
`(aktueller Mittelwert - vorheriger Mittelwert) * 60 / verstrichene Sekunden`
berechnet und hat damit die Einheit pro Minute. `NULLIF(elapsed_seconds, 0)`
schließt eine Division durch null zusätzlich aus. Bei einer vollständig
fehlenden Minute bleibt die Ableitung `NULL`, statt eine Änderung über eine
längere Lücke fälschlich als 60-Sekunden-Änderung darzustellen.

`$__interval` kommt in der Analyse nicht vor. Eine Änderung des Dashboard-
Zeitraums ändert deshalb weder Bucketbreite noch Ableitungsdefinition. Der
erste und eventuell letzte Bucket eines ausgewählten Zeitraums kann nur einen
Teil einer Minute enthalten; für den ersten sichtbaren Bucket gibt es mangels
Vorgänger im ausgewählten Bereich keine Ableitung.

## Abfragen

### Kesseldampf – Dynamik

```sql
WITH minute_values AS (
  SELECT time_bucket(INTERVAL '1 minute', time) AS time,
         avg(value)::double precision AS smoothed_value
  FROM sensor_measurements
  WHERE sensor_id = 'vapor-temp'
    AND $__timeFilter(time)
  GROUP BY 1
), lagged AS (
  SELECT time, smoothed_value,
         lag(smoothed_value) OVER (ORDER BY time) AS previous_value,
         EXTRACT(EPOCH FROM time - lag(time) OVER (ORDER BY time))::double precision AS elapsed_seconds
  FROM minute_values
)
SELECT time,
       smoothed_value AS "Kesseldampf (60-s-Mittel)",
       CASE WHEN elapsed_seconds = 60
            THEN (smoothed_value - previous_value) * 60.0 / NULLIF(elapsed_seconds, 0)
       END AS "dT/dt (°C/min)"
FROM lagged
ORDER BY time;
```

### EC – Dynamik

Die EC-Abfrage ist identisch aufgebaut, verwendet aber `sensor_id = 'ec-1'`
und benennt die Reihen `EC (60-s-Mittel)` und `dEC/dt (µS/cm/min)`.

### Prozessanalyse

```sql
SELECT time_bucket(INTERVAL '1 minute', time) AS time,
       avg(value) FILTER (WHERE sensor_id = 'vapor-temp')::double precision AS "Kesseldampf (60-s-Mittel)",
       avg(value) FILTER (WHERE sensor_id = 'ec-1')::double precision AS "EC (60-s-Mittel)"
FROM sensor_measurements
WHERE sensor_id IN ('vapor-temp', 'ec-1')
  AND $__timeFilter(time)
GROUP BY 1
ORDER BY 1;
```

### Temperaturdifferenz

```sql
WITH aligned AS (
  SELECT time_bucket(INTERVAL '1 minute', time) AS time,
         avg(value) FILTER (WHERE sensor_id = 'vapor-temp')::double precision AS vapor_temperature,
         avg(value) FILTER (WHERE sensor_id = 'ec-temp')::double precision AS ec_temperature
  FROM sensor_measurements
  WHERE sensor_id IN ('vapor-temp', 'ec-temp')
    AND $__timeFilter(time)
  GROUP BY 1
)
SELECT time,
       vapor_temperature - ec_temperature AS "Kesseldampf minus EC-Temperatur"
FROM aligned
WHERE vapor_temperature IS NOT NULL
  AND ec_temperature IS NOT NULL
ORDER BY time;
```

### Kühler – Verlauf

```sql
SELECT time_bucket(INTERVAL '1 minute', time) AS time,
       avg(value)::double precision AS "Kühler (60-s-Mittel)"
FROM sensor_measurements
WHERE sensor_id = 'cooler-temp'
  AND $__timeFilter(time)
GROUP BY 1
ORDER BY 1;
```

## Performance und Grenzen

Jede Abfrage begrenzt den Hypertable-Zugriff mit `$__timeFilter(time)` und
einem einzelnen `sensor_id` oder einer kleinen festen `sensor_id`-Liste. Das
passt zu den vorhandenen Indizes auf `(sensor_id, time DESC)` und `time`; die
Aggregation liefert über zwölf Stunden höchstens ungefähr 720 Zeitpunkte pro
Reihe an Grafana statt der hochfrequenten Rohdaten.

Die Ausrichtung erfolgt nach Minuten-Buckets, nicht durch Interpolation. Bei
der Temperaturdifferenz werden nur Minuten mit Werten beider Sensoren gezeigt.
Einzelne Ausreißer innerhalb einer Minute können den Mittelwert weiterhin
beeinflussen, kurze Vorgänge unter einer Minute werden geglättet, und partielle
Rand-Buckets können weniger Messungen enthalten. Diese Signale sollten daher
vor dem ersten realen Rohbrand ausschließlich explorativ gelesen werden.
