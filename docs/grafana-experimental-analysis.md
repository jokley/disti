# DISTI: experimentelle Prozessanalyse

## A. Dateien und Umfang

Neu: `backend/disti/process_analysis/{__init__,models,config,features,states,analyzer,service}.py`,
`backend/migrations/004_process_analysis.sql`, `backend/tests/test_process_analysis.py`.
Geändert: `README.md`, `backend/disti/repository.py`, `backend/disti/api/app.py`,
`backend/tests/test_grafana_dashboard.py`, `grafana/dashboards/Distillation.json`, diese Dokumentation.

Die Rohdatentabelle, Sensorerfassung, Hardware-Treiber, Notifications und
Steuerung bleiben unverändert. Die alte SQL-basierte experimentelle Dashboard-Zeile
wird ersetzt. Operative Panels und Rohdatenbereich bleiben bestehen.

## B. Modulstruktur und Verantwortlichkeiten

```text
backend/disti/process_analysis/
├── __init__.py   öffentliche Imports
├── config.py     unveränderliche experimentelle AnalysisConfig
├── models.py     AnalysisInput, Features, DetectorDetails, AnalysisResult
├── features.py   kausale Zeitfenster und lineare Trends
├── states.py     stabile ProcessState-Enum
├── analyzer.py   ProcessAnalyzer.reset()/update(), ohne externe Infrastruktur
└── service.py    Rebuild-Orchestrierung und einzelner Live-Persistenzaufruf
```

Repository: nur Rohdatenaggregation und Persistenz. Flask: nur Requestvalidierung
und Serviceaufruf. Grafana: nur gespeicherte Analysewerte und Anzeigeformatierung.

Ein anderer Analyzer benötigt denselben Konstruktor-, reset- und update-Vertrag,
einen `detector_name` und generische Resultfelder. `AnalysisService(...,
analyzer_type=OtherAnalyzer)` ist der kleine Austauschpunkt; keine Registry oder
Plugin-Factory. Für weitere Detectoren dürfen deren interne typisierte Details
angepasst werden; die generischen DB-Spalten bleiben erhalten. Die explizite
API-Versionsprüfung muss bei Freigabe einer neuen Implementierung erweitert
werden. Parallelbetrieb bedeutet getrennte Analyzer-Instanzen pro Detector/Version.

## C. Schema, Migration und Inbetriebnahme

`004_process_analysis.sql` legt eine additive PostgreSQL-Tabelle an:

- Schlüssel: `(time, detector_name, algo_version)`.
- Physik: `vapor_temp`, `raw_mv`, `pt_raw_mv`, `dtdt`, geglättete EC-Werte.
- Features: Minimum, Abstand vom Minimum, drei Trends und Trendänderungen über eine Minute.
- Detector: Name, Version, generischer Score, boolescher Alarm.
- Interpretation: `process_state`, `ended`.
- `details JSONB`: typisierte interne CUSUM-Diagnose als Persistenzformat,
  einschließlich Mittelwert, Varianz, Sigma, Warmup-Zähler, Freeze, z, S und
  Sekunden seit Plateau.

`run_id` wurde aus `process_analysis`, AnalysisInput und AnalysisResult entfernt.
Auch Rohmessungen mit `sensor_measurements.run_id = NULL` werden analysiert.
Die PK erlaubt mehrere Detectoren und Versionen pro Analysezeitpunkt.
Ein zusätzlicher Index auf `(detector_name, algo_version, time DESC)` unterstützt
Grafana. Der vorhandene Rohdatenindex `(sensor_id, time DESC)` bleibt erhalten;
keine Veränderung am Rohdaten-Hypertable.

Rebuilds löschen ausschließlich den angeforderten Bereich `[from, to)` für
Detector/Version und schreiben die neuen Ergebnisse in derselben Transaktion.
Auch veraltete Zeilen ohne neu berechenbaren Bucket werden entfernt. Andere
Zeiträume und Versionen bleiben erhalten. Live-Punkte verwenden denselben PK
mit Upsert. Rohdaten werden ausschließlich gelesen.

Nach Bereitstellung des aktualisierten Backends im bestehenden Stack:

```sh
docker compose exec api python -m entrypoints.migrate
```

Die vorhandene Migration-Entrypoint-Konvention wird verwendet. Anschließend
Grafana das aktualisierte provisionierte Dashboard laden lassen. In dieser
Arbeitsumgebung wurde kein bestehender DISTI-Stack migriert oder neu gestartet.
Ein automatischer Live-Worker wird mit dieser Änderung noch nicht gestartet;
Dashboard-Daten entstehen zunächst durch Rebuild-Aufrufe.

## D. Analyzer-State und Berechnungsreihenfolge

Eine Instanz verarbeitet die kontinuierliche Sensor-Zeitreihe, auch über mehrere
Brände. `reset()` löscht Zeitfenster, Prozess-/Endzustand, Plateau, Tmax,
Fehlerdauer, Baseline, S und Alarm. Zeitstempel müssen Zeitzonen enthalten und
streng steigen. Die API normalisiert Eingaben nach UTC; Run-Zuordnungen haben
keinen Einfluss auf den Analyzer.

1. Datenlücke oder ungültiger Sensor: keine neuen Features/Detector-Entscheidungen.
2. Gültiger Brandstart bei T >= 75 °C; ein heiß begonnener historischer Zeitraum kann
   beim ersten gültigen Punkt starten. Unter 75 °C: IDLE vor dem ersten Start.
3. dT/dt ist die Steigung einer linearen Regression der Temperatur über das
   kausale 60-s-Fenster, in °C/min. Dies glättet die kurzfristige Dynamik; es ist
   nicht die Differenz ungeglätteter Einzelwerte.
4. Plateau wird beim dritten aufeinanderfolgenden passenden Bucket bestätigt;
   dieser Bestätigungszeitpunkt ist `plateau_time`, ohne rückwirkende Änderung.
5. Baseline startet frühestens 300 s nach Plateau. Erster Wert initialisiert
   mu mit raw_mv und Varianz mit 4. Danach gilt:

   ```text
   alpha = 1 - 0.5 ** (bucket_seconds / baseline_half_life_seconds)
   delta = raw_mv - mu_previous
   mu = mu_previous + alpha * delta
   var = (1-alpha) * (var_previous + alpha * delta**2)
   sigma = max(sqrt(var), sigma_min_mv)
   ```

6. Freeze wird ab 84.5 °C verriegelt und bleibt bis zum neuen Brand/reset
   aktiv, auch wenn die Temperatur danach wieder unter das Gate fällt.
7. z nutzt die Baseline nach dem jeweiligen Baseline-Update. Erst nach 30
   gültigen Baseline-Samples wird z bereitgestellt. Bei Freeze bleibt die
   Baseline unverändert. CUSUM läuft erst ab 84 °C und fertigem Warmup:

   ```text
   z = (raw_mv - mu) / sigma          # kein Clipping im Standard
   S = max(0, 0.995 * S_previous + z - 0.75)
   Alarm EIN bei S > 8; AUS bei S < 2.4; dazwischen Zustand beibehalten
   detector_score = min(S / 8, 2)
   ```

8. Alarm bei T < 86 °C: NACHLAUF_ENTWICKELT; ab 86 °C:
   NACHLAUF_WAHRSCHEINLICH. Das sind experimentelle Interpretationen.
9. Ende bei Abfall >= 1.5 °C unter laufendes Tmax, T < 75 °C oder
   kontinuierlich >= 180 s ungültigem Sensor. S=0, Alarm=false, ENDE.
   Nach ENDE wird ein neuer Brand erst nach einem gültigen Wert unter 75 °C
   und anschließender Rückkehr auf >= 75 °C freigegeben. Ein explizites
   reset() setzt den Analyzer zurück.

Nach dem bestehenden Plateau beginnt VORLAUF. Der zweistufige Ausgang verwendet
unverändert berechnete EC-Features und dieselben aktuellen Plateau-Kriterien:

- VORLAUF → VORLAUF_AUSKLANG: `trend_3m > -0.10` mV/min und
  `trend_accel_3m > 0.0` mV/min², kontinuierlich mindestens 60 s.
- VORLAUF_AUSKLANG → MITTELLAUF: anschließend `trend_3m >= -0.05` und
  `trend_5m >= -0.05` mV/min, bei weiter gültigem Plateau mindestens 120 s.
- VORLAUF_AUSKLANG fällt bei `trend_3m <= -0.10` wieder auf VORLAUF zurück.
  Dafür wird dieselbe Grenze verwendet, keine zusätzliche Rückfallschwelle.
- MITTELLAUF bleibt verriegelt; vorhandene Nachlauf- und Endeentscheidungen
  haben Vorrang. Neuer Brand oder reset() löscht Vorlauf-State und Persistenz.

Persistenz wird über Zeitstempel ab dem ersten passenden Bucket gemessen.
Der erste MITTELLAUF-Persistenzpunkt liegt nach Erreichen von VORLAUF_AUSKLANG.
Lücken, Sensorfehler, fehlende benötigte Features, verlorenes Plateau oder
nicht erfüllte Kriterien unterbrechen die betreffende Persistenz. Das
Plateau wird weiterhin ausschließlich durch die bestehende Temperatur- und
dT/dt-Logik definiert. Ohne erstmals bestätigtes Plateau bleibt AUFHEIZEN.

Alle sechs neuen Vorlauf-Parameter stehen in config.py:
`heads_exit_trend_3m_threshold=-0.10`, `heads_exit_accel_min=0.0`,
`heads_exit_persistence_seconds=60`, `heads_middle_trend_3m_min=-0.05`,
`heads_middle_trend_5m_min=-0.05`, `heads_middle_persistence_seconds=120`.
Keine obere Trendgrenze und kein zusätzlicher Detector wurden ergänzt.
`rise_from_min_5m` bleibt diagnostisch; keine automatische Schnittsteuerung.

## E. Parameter und Fensterspezifikation

Alle Schwellen in `config.py`. Standard: 20 s Buckets; Start 75 °C;
Plateau dT/dt < 1 °C/min, drei gültige Buckets; Delay 300 s;
Halbwertszeit 600 s; Warmup 30 Samples; Varianz 4 mV²; Sigma >= 1.5 mV;
Freeze 84.5 °C; Detection-Gate 84 °C; Bestätigungs-Gate 86 °C;
k=.75, h=8, Leak=.995, Alarm-Aus=0.3*h=2.4; Scoremaximum=2;
z_clip=None; Endeabfall 1.5 °C; Fehlerdauer 180 s; Version `cusum-v1`.

Strenges Plateau ist vorbereitet, aber aus: T >= 81.8 °C und
-0.2 <= dT/dt <= 0.3 °C/min. Parameteränderungen für historische Vergleiche
sollten eine neue `algo_version` bekommen; Rebuild mit unverändertem
Versionsnamen ersetzt ansonsten die vorherigen Resultate.

EC raw_mv > 200 mV ist ungültig. Der reale ADS1115-Treiber berechnet
`raw_count * full_scale_volts * 1000 / 32768`: raw_mv ist mV,
auch beim PT1000-Kanal. Die experimentelle Absteckprüfung verwendet deshalb
3300 mV mit zentral konfigurierter ±100-mV-Toleranz. Fehlende Sensorwerte
sind eine Datenlücke; nicht endliche Werte oder explizite ungültige Qualität
sind Sensorfehler. `good` und die bestehende Testqualität `simulated` werden
akzeptiert. Qualitätsfehler eines Kernkanals machen den Bucket ungültig.

Featurefenster sind `(time-window, time]`, also bei lückenlosen 20-s-Buckets
3/9/15 Werte für 1/3/5 Minuten. EC-Mittelwerte sind arithmetisch; Minimum und
rise_from_min verwenden das 5-min-Fenster. `trend_1m` bleibt eine Regressionssteigung in mV/min (mindestens zwei Werte).
`trend_3m` und `trend_5m` bleiben Differenzen des geglätteten
5-min-Mittelwerts:

```text
trend_3m(t) = (raw_mv_5m(t) - raw_mv_5m(t - 3 min)) / 3 min
trend_5m(t) = (raw_mv_5m(t) - raw_mv_5m(t - 5 min)) / 5 min
trend_accel_3m(t) = (trend_3m(t) - trend_3m(t - 1 min)) / 1 min
trend_accel_5m(t) = (trend_5m(t) - trend_5m(t - 1 min)) / 1 min
```

Trendeinheit: mV/min; Trendänderung: mV/min². Es wird keine rohe zweite
Ableitung berechnet. Der Vergleichsabstand ist zentral als
`trend_accel_lag_seconds=60` konfiguriert. Exakte Zeitstempel statt Zeilenabstände;
keine Interpolation und keine Zukunftsdaten. Für diese Trends muss die
5-min-Glättung an beiden Vergleichszeitpunkten vollständig aufgewärmt sein.
Der erste vollständige Glättungswert kommt konservativ nach 300 s gültiger
kontinuierlicher Vorgeschichte. Damit ist `trend_accel_3m` frühestens nach
540 s und `trend_accel_5m` nach 660 s verfügbar. Vorher: NULL. Die angezeigten
EC-Mittelwerte selbst dürfen weiterhin Teilfenster enthalten.

Lücken, Sensorfehler und reset löschen auch die zusätzliche Trendhistorie.
Nach einer Lücke wird die Vorgeschichte neu aufgebaut. Beide Acceleration-Werte
sind reguläre double-precision-Spalten in Migration 004, nicht JSONB-Diagnose.
Migration 004 wurde direkt auf das zeitbasierte Modell angepasst, weil sie noch
nicht produktiv angewendet wurde. CREATE TABLE IF NOT EXISTS aktualisiert keine
bereits lokal angelegte alte Tabelle. Das Schema bleibt für die Vorlauf-/Nachlaufanpassung unverändert. CUSUM-Aufbau,
Trend-, trend_accel- und rise_from_min-Berechnungen bleiben erhalten; geändert
werden h, die daraus abgeleitete Ausschaltgrenze und die Vorlauf-Zustandsauswertung.

Bei fehlenden Buckets erzeugt der Service explizite leere 20-s-Punkte.
Status DATENLUECKE; Baseline, S und Alarm bleiben erhalten. Zeitfenster und
noch unbestätigte Plateau-Persistenz werden geleert, damit kein Trend über
Lücken entsteht. Eine direkt gelieferte übersprungene Zeit wird ebenfalls als
DATENLUECKE ausgegeben. Live deshalb jeden Bucket einschließlich leerer Buckets
liefern. Lücken unterbrechen auch den Nachweis eines kontinuierlichen
Sensorfehlers; sie beenden den Brand nicht. Unterhalb des Detection-Gates
bleibt CUSUM ebenfalls eingefroren, bis Gate oder Endkriterium greift.

## F. API

```http
POST /api/analysis/rebuild
Content-Type: application/json

{
  "from": "2026-10-09T00:00:00+02:00",
  "to": "2026-10-10T00:00:00+02:00",
  "algo_version": "cusum-v1"
}
```

`from` und `to` bestimmen ausschließlich das Speicherfenster. `run_id` wird
nicht unterstützt. Der Rebuild liest alle relevanten Rohdaten vor dem letzten
abgeschlossenen Bucket, unabhängig von Run-Zuordnungen, aggregiert sie mit der
bestehenden 20-s-Bucket-Logik und verarbeitet sie mit einem frischen Analyzer
chronologisch durch dieselbe update()-Logik wie live.

Die vollständige verfügbare Vorgeschichte wird automatisch eingelesen: Ein
festes 10-/30-min-Warmup wäre für die fortgeschriebene und gegebenenfalls
verriegelte Baseline sowie CUSUM nicht exakt. Die Featurefenster sind begrenzt,
der Detector-State dagegen nicht. Nur Bucket-Startzeiten >= from werden
persistiert; `to` ist exklusiv. Offene Buckets und Zukunftsdaten werden
nicht berechnet. Der gesamte angeforderte Speicherbereich wird atomar ersetzt.
Keine Änderung an sensor_measurements; keine künstlichen UUIDs.

Antwort: `points_written`, `detector_name`, `algo_version`, `completed_until`.
Ungültiges JSON, Zeitbereich, Zeit ohne Zeitzone, run_id oder unbekannte Version:
HTTP 400. Leerer gültiger Bereich kann null Punkte liefern.

Der Aufruf bleibt synchron. Für große Datenbestände werden Vorgeschichte und
Ergebnisse derzeit im Speicher gehalten; vorhandene Gunicorn-/Proxy-Zeitlimits
berücksichtigen. Gleichzeitige Rebuilds und Live-Schreibzugriffe für denselben
Zeitraum/Detector/Version durch den Betreiber serialisieren.
Direkter API-Zugang: Port 5000; hinter dem vorhandenen Nginx-Prefix:
`/backend/api/analysis/rebuild`.

## G. Grafana

Filter: Grafana-Zeitfenster, Detector, Algorithmusversion. Der bestehende Dashboard-UID
bleibt erhalten. Alle neuen Panelabfragen lesen ausschließlich `process_analysis`.

- EC Prozesssignal: raw_mv, 1-/5-min-Mittel und CUSUM-Baseline aus details.
- Nachlauf-Detector: Nachlauf-Score 0–100, Alarm, CUSUM S, z.
  Anzeige `50 * detector_score` ist keine Wahrscheinlichkeit: 0/25/50/75/100
  entsprechen S/h = 0/0.5/1/1.5/≥2. Die technische Skala ist unabhängig vom
  Boolean Alarm. Die sichtbare Schwelle 50 bedeutet S=h; Alarm EIN bleibt
  strikt S>h. Schwellen 4/8 gelten für CUSUM S auf der rechten Achse.
- Vergleichsmarker: rise_from_min, drei Trends sowie trend_accel_3m/5m;
  Trends mit mV/min und Trendänderungen mit mV/min² auf rechter Achse.
- Temperatur: vapor_temp sowie dT/dt auf rechter Achse.
- Prozessstatus: State timeline mit stabilen Enum-Werten/Farben.
- Analyse – letzter Wert: Kesseldampf, Score, Alarm und Status des letzten
  Analysepunkts im gewählten Grafana-Zeitfenster.

Die physikalischen Werte sind detectorunabhängig. Zusätzliche CUSUM-Diagnosen
bleiben optionale JSON-Felder; bei anderen Detectoren ohne diese Schlüssel
zeigen die betreffenden Reihen NULL. Historische Brände werden ausschließlich
über Grafana-Zeitfenster verglichen. Ohne Rebuild/Live-Writer bleiben
Analysepanels leer. Grafana-Refresh berechnet keine neuen Analysepunkte.

## H. Tests

DB-freie Analyzer-/Featuretests und SQLite-Persistenz-/Flasktests prüfen:
Plateau-Persistenz, 20-s-Sequenz, Temperatursteigung, Zeitfenster, Mittelwerte,
Minimum/Anstieg, drei Trends, EW-Mittelwert und Varianz, Warmup, Sigma-Untergrenze,
Freeze-Verriegelung, z, standardmäßig deaktiviertes Clipping, CUSUM-Formel,
Alarm-Grenze/Hysterese, Temperatur-Gates, Ende, Fehlerdauer, Datenlücken,
Qualität, nicht endliche Werte, Reset/Neustart, Run-Unabhängigkeit, kausale Präfixe,
fehlende und partielle Buckets, idempotenten Rebuild, historische/inkrementelle
Übereinstimmung und unveränderte Rohdaten. Dashboardtests prüfen rein lesende
Analyseabfragen, Filter, letzte Werte, Einheiten und CUSUM-Diagnosen.

```sh
PYTHONPATH=backend python -m pytest backend/tests -q
```

Zusätzliche Trend-Dynamiktests prüfen konstantes Signal, linearen Anstieg,
beschleunigten Anstieg, Erholung eines negativen Trends, exakte Warmup-Grenzen,
Lücken, Kausalität, reguläre Persistenzspalten, historische/Live-Übereinstimmung
und die Unabhängigkeit von CUSUM/Alarm gegenüber Trendfeatures. Nur die neue
Vorlauf-Zustandsauswertung verwendet die vorhandenen Trends.

Zusätzliche zeitbasierte Tests prüfen historische NULL-Run-Messungen vom
09.10.2026, automatisches Warmup, keine Persistenz außerhalb des Speicherfensters,
gezieltes Ersetzen einschließlich leerer Bereiche, Erhalt anderer Versionen,
Transaktions-Rollback und mehrere getrennte Brände mit Live-/Replay-Gleichheit.
Auch ein Teil-Rebuild nach über 30 Minuten übernimmt die ursprüngliche Baseline.
Neue Vorlauf-/Nachlauftests prüfen h=8, abgeleitete Hysterese, graduellen
Score unabhängig vom Alarm und dessen Persistenz, beide Vorlauf-Stufen,
Persistenzgrenzen, Acceleration-Spikes, Rückfall, Plateau-/Featureverlust,
Datenlücken, Sensorfehler, MITTELLAUF-Verriegelung sowie Nachlauf-/Endevorrang.
Ein synthetischer abklingender EC-Verlauf bestätigt mit echten Featureformeln
identische gespeicherte Zustandswechsel live und im vollständigen/Teil-Rebuild.

Die vollständige Suite umfasst Backend- und Watchdogtests; das aktuelle Ergebnis
ist im Abschlussbericht dokumentiert. Ein gerendertes Grafana-UI und die echte
TimescaleDB-Laufzeit sind zusätzliche Integrationsprüfungen.

## I. Historische Brände vom 09.10.2026 neu berechnen

Nach Bereitstellung des Backends und Anwendung von Migration 004 einmal den
gesamten 09.10.2026 in Europe/Berlin (UTC+02:00) berechnen:

```sh
curl --fail-with-body -X POST http://localhost:5000/api/analysis/rebuild \
  -H 'Content-Type: application/json' \
  -d '{"from":"2026-10-09T00:00:00+02:00","to":"2026-10-10T00:00:00+02:00","algo_version":"cusum-v1"}'
```

Anschließend auf den jeweiligen Brand in Grafana zoomen und dieselbe Version
wählen. Die Rohdaten brauchen keine Zuordnung zu distillation_runs. Die experimentellen
Vorlaufgrenzen müssen anschließend an den historischen Bränden auf Plausibilität
geprüft werden; es wurde nicht auf sensorische Referenzzeiten gefittet. In der
aktuellen Arbeitsumgebung ist die lokale PostgreSQL-Datenbank leer, daher sind
keine historischen Zustandswechsel oder eine Plausibilitätsbewertung verfügbar.

## J. Späterer Live-Aufruf

```python
from disti.process_analysis import AnalysisConfig, AnalysisInput, ProcessAnalyzer
from disti.process_analysis.service import AnalysisService

config = AnalysisConfig()
service = AnalysisService(repository, config)
analyzer = ProcessAnalyzer(config)

# Genau einmal pro abgeschlossenem Bucket, aufsteigend, einschließlich Lücken:
result = service.save_completed_point(analyzer, AnalysisInput(
    time=bucket_start_utc,
    vapor_temp=avg_vapor_temp, raw_mv=avg_ec_raw_mv,
    pt_raw_mv=avg_pt_raw_mv,
    sensor_invalid=has_invalid_quality,
))
```

Alternativ kann der Live-Caller die Aggregation direkt dem Service überlassen:

```python
result = service.process_completed_bucket(analyzer, bucket_start_utc)
```

Dieser Aufruf liest über `repository.analysis_buckets(..., start=bucket_start)`
nur den einen abgeschlossenen Bucket; ein leerer Bucket wird als DATENLUECKE
persistiert. Die laufende Instanz wird behalten; niemals für jeden Live-Punkt
neu erstellen und niemals den ganzen Brand regelmäßig neu berechnen.

Nach Prozessneustart verfügbare Sensor-Vorgeschichte einmal durch dieselbe update-Logik replayen,
dann fortsetzen. Noch kein persistenter Analyzer-Checkpoint. Wenn eine
Persistenzoperation fehlschlägt, vor einem Retry den Analyzer durch Replay
wiederherstellen; update darf für denselben Zeitstempel nicht doppelt laufen.

## K. Offene Annahmen und Risiken

- Plateau ist validierter als Vorlaufende; automatische Schnittentscheidungen,
  Notifications und Aktuatorzugriffe sind nicht implementiert.
- 200 mV, PT1000-Toleranz, Freeze- und Temperaturschwellen sind experimentell.
  Der vorhandene einfache MockSensorReader liefert EC >200 mV und keinen
  PT1000-Rohkanal; dieser alte Mock ist daher kein fachlich gültiger Analysebrand.
- Wird Freeze vor Baseline-/Warmupabschluss erreicht, wird kein Nachlaufalarm
  erzeugt. Das ist konservativ und in details erkennbar.
- Keine Interpolation, keine Warmup-Samples während Lücken. Lange Lücken führen
  weder zu erfundenem Verlauf noch automatisch zum Ende.
- Optionales Vorlauf-Ausklang/Mittellauf-Mapping wartet auf echte Validierung.
- Dashboard-SQL wurde strukturell und zusätzlich soweit möglich gegen PostgreSQL
  geprüft; ein gerendertes Grafana-UI und echte TimescaleDB-Laufzeit sind getrennte
  Integrationsprüfungen.
