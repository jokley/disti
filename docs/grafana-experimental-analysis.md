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
├── service.py    Rebuild-Orchestrierung und einzelner Live-Persistenzaufruf
└── worker.py     kontinuierlicher einzelner Live-Consumer
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
Der Compose-Service `analysis-worker` aktiviert die kontinuierliche Analyse beim
nächsten Start des aktualisierten Stacks. Er verwendet dasselbe Backend-Image
mit eigenem Entrypoint; weder Gunicorn-Worker noch Hardware-Prozess starten
zusätzliche Analyseschleifen. Keine produktive Bereitstellung in dieser Sitzung.

## D. Analyzer-State und Berechnungsreihenfolge

Eine Instanz verarbeitet die kontinuierliche Sensor-Zeitreihe, auch über mehrere
Brände. `reset()` löscht Zeitfenster, Prozess-/Endzustand, Plateau, Tmax,
Fehlerdauer, Baseline, S und Alarm. Zeitstempel müssen Zeitzonen enthalten und
streng steigen. Die API normalisiert Eingaben nach UTC; Run-Zuordnungen haben
keinen Einfluss auf den Analyzer.

1. Datenlücke oder ungültiger Sensor: keine neuen Features/Detector-Entscheidungen.
2. Der bestehende interne Detector startet unverändert bei T >= 75 °C;
   diese Regel steuert Baseline/CUSUM, nicht den sichtbaren Aufheizbeginn.
   Der sichtbare Lifecycle startet ohne absolute Temperaturgrenze aus BEREIT.
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
   NACHLAUF (bisherige zweite Stufe, nur umbenannt).
9. Interner Detector-Stopp weiterhin bei Abfall >= 1.5 °C unter laufendes
   Tmax, T < 75 °C oder kontinuierlich >=180 s ungültigem Sensor. S=0,
   Alarm=false. Nach Stopp startet dieser interne Detector erst nach einem
   gültigen Wert unter 75 °C und erneuter Rückkehr auf >=75 °C. Die vorhandene
   boolesche Spalte `ended` beschreibt weiterhin diesen internen Stopp; sie
   ist kein sichtbarer Prozess-State. Damit bleiben Baseline, CUSUM, Score,
   Alarm und alle diagnostischen Formeln unverändert.

### Sichtbarer Betriebs-Lifecycle

BEREIT → AUFHEIZEN → VORLAUF → VORLAUF_AUSKLANG → MITTELLAUF →
NACHLAUF_ENTWICKELT → NACHLAUF → ABKÜHLEN → BEREIT.
DATENLUECKE und SENSOR_UNGUELTIG bleiben technische Qualitätsüberlagerungen,
keine zusätzlichen normalen Prozessphasen. Der physische Zustand bleibt
während solcher Überlagerungen intern erhalten.

- Initialzustand ist BEREIT. `dT/dt > 0.20` °C/min über 60 s startet die
  sichtbare Aufheizphase, unabhängig von absoluter Temperatur und EC. Ein
  kurzer Spike reicht nicht. Beim Start mitten in einer Bewegung ohne
  vollständige Vorgeschichte ist BEREIT eine Initialannahme.
- Nach Erreichen von NACHLAUF bleibt diese physische Phase bis zum
  Abkühlbeginn bestehen; das boolesche CUSUM-Alarmsignal wird dadurch nicht
  verändert. ABKÜHLEN benötigt `dT/dt <= -0.50` für mindestens 60 s und
  mindestens 2.0 °C Abfall gegenüber dem Maximum der letzten 300 s. Ein
  interner Detector-Stopp alleine erzeugt keinen neuen sichtbaren Endzustand.
- ABKÜHLEN → BEREIT: kausales 180-s-Fenster mit Median `abs(dT/dt) <=0.10`
  °C/min und mindestens 80 % der Werte `abs(dT/dt) <=0.20`. Das toleriert
  einzelne Ausreißer, ohne fortgesetzte Abkühlung als Ruhe einzustufen. Es gibt
  keine Raumtemperaturgrenze. Danach kann ein neuer positiver Anstieg starten.
- Lücken oder ungültige Sensoren setzen die neuen Timer/Fenster zurück.
  Nachfolgende gültige Buckets bauen sie neu auf. Keine Interpolation.

Neue zentrale Config-Werte: `heating_start_dtdt_min=0.20`,
`heating_start_persistence_seconds=60`, `cooling_dtdt_max=-0.50`,
`cooling_persistence_seconds=60`, `cooling_temperature_drop=2.0`,
`cooling_peak_window_seconds=300`, `ready_window_seconds=180`,
`ready_median_abs_dtdt_max=0.10`, `ready_bucket_abs_dtdt_max=0.20`,
`ready_required_fraction=0.80`.

Die angezeigte Vorlauf-/Mittellauf-Phase entsteht weiterhin ausschließlich aus dT/dt.
Die vorhandene Plateau-Erkennung für CUSUM-Baseline und EC-Referenz bleibt
unverändert und ist unabhängig von der neuen Anzeigeentscheidung. Ebenso
bleiben bestehende Prozessstart-/Endegrenzen und Nachlauf-Temperatur-Gates
unverändert. Die Vorlauf-Übergänge selbst verwenden keine absolute Temperatur.

1. AUFHEIZEN: Erst ein beobachtetes `dT/dt >= 1.0` °C/min gibt die nachfolgenden
   Übergänge frei. Ein heiß gestarteter, konstanter Verlauf ohne Aufheizen
   erhält keine automatische VORLAUF-Anzeige, auch wenn die CUSUM-Baseline
   bereits ein Plateau erkannt hat.
2. VORLAUF: nach dieser Aufheizphase `dT/dt <= 0.30` für mindestens 40 s.
   Nicht passende Werte, Lücken oder Sensorfehler unterbrechen die Persistenz.
3. VORLAUF_AUSKLANG: vollständig aufgewärmtes, kausales 120-s-Fenster
   `(t-120 s, t]` mit `median(abs(dT/dt)) <= 0.12` °C/min und mindestens
   80 % der Werte `abs(dT/dt) <= 0.20` °C/min. Keine Interpolation. Bei
   20-s-Buckets sind das sechs Werte; ein einzelner Ausreißer ist möglich.
4. MITTELLAUF: dieselbe stabile Fensterbedingung muss nach VORLAUF_AUSKLANG
   noch mindestens 90 s bestätigt werden. Eine unstabile Fensterphase
   unterbricht die Bestätigung; anschließend beginnt sie neu. Mit 20-s-
   Buckets erfolgt eine ununterbrochene Bestätigung beim ersten verfügbaren
   Punkt nach 90 s, also nach 100 s. MITTELLAUF bleibt verriegelt.

Datenlücken und ungültige Sensorwerte leeren das dT/dt-Fenster und die Timer;
die vorher beobachtete Aufheizphase bleibt bekannt. Die schon erreichte Stufe
bleibt erhalten, wird während der Lücke aber durch den bestehenden Datenstatus
überlagert. Der unveränderte interne Detector-Start/-Stopp und reset() löschen seine
Vorlauf-Historie. Nachlauf und der sichtbare Abkühl-Lifecycle haben Vorrang. Keine Referenzzeiten und keine
EC-, Trend- oder Recovery-Bedingung für die Übergänge.

Zentrale Werte in config.py:
`heating_detect_dtdt_min=1.0`, `vorlauf_start_dtdt_max=0.30`,
`vorlauf_start_persistence_seconds=40`, `vorlauf_ausklang_window_seconds=120`,
`vorlauf_ausklang_median_abs_dtdt_max=0.12`,
`vorlauf_ausklang_bucket_abs_dtdt_max=0.20`,
`vorlauf_ausklang_required_fraction=0.80`, `vorlauf_middle_confirm_seconds=90`.
Die vorherigen EC-Vorlauf-Entscheidungsparameter wurden entfernt.

Alle vorhandenen EC-Features werden unverändert berechnet und gespeichert.
Die Plateau-Referenz ist weiterhin `raw_mv_1m` am bestätigten Baseline-Plateau-
Eintritt, konstant für den Prozess. `ec_drop_from_plateau` ist Referenz minus
aktuelles 1-min-Mittel, `ec_min_since_plateau` das kleinste 1-min-Mittel seit
Plateau und `ec_recovery_from_min` der Abstand zu diesem Minimum. Vor diesem
Plateau und in ungültigen Buckets NULL. Lücken erhalten Referenz/Minimum,
Interner Detector-Stopp und neuer Prozess löschen beides. Diese Größen sind nur diagnostisch.

## E. Parameter und Fensterspezifikation

Alle Schwellen in `config.py`. Standard: 20 s Buckets; interner Detector-Start 75 °C;
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
Migration 004 definiert weiterhin das zeitbasierte Schema. Die additive,
wiederholt ausführbare Migration `005_plateau_ec_features.sql` ergänzt vier
reguläre `double precision`-Spalten: `ec_plateau_ref`, `ec_drop_from_plateau`,
`ec_min_since_plateau`, `ec_recovery_from_min`. Kein zusätzliches JSONB-Feld,
keine neue Tabelle. Bestehende Zeilen bleiben zunächst NULL und werden bei
einem zeitbasierten Rebuild reproduzierbar gefüllt. Migration 004 bleibt
unverändert; Migration 005 über den vorhandenen Entrypoint anwenden.

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

## G. Grafana: Betriebsansicht

Die Dashboard-UID und Detector-/Versionsfilter bleiben erhalten. Die Live-Ansicht
verwendet den Zeitraum bis `now` und weiterhin 10 s Refresh. Detector/Version
bleiben als versteckte Variablen mit bestehenden Defaults erhalten. Kurven und
Timeline verwenden den Zeitfilter; der aktuelle State zeigt bewusst global den
letzten vorhandenen Analysepunkt, auch beim historischen Zoom.

Hauptbereich, von oben nach unten:

- **Aktueller Prozessstatus**: große Stat mit sämtlichen bestehenden State-
  Mappings, ausschließlich letzter gespeicherter process_state ohne Zeitfilter, als String. Keine neue
  State- oder transition_reason-Logik; keine Berechnung der State-Dauer.
- **Prozessstatus**: kompakte Timeline aus gespeicherten Zuständen.
- **Aktuelle Prozesswerte**: Kesseldampf und Kühler als kompakte Temperaturwerte neben dem aktuellen
  Prozessstatus; darunter Timeline und dominanter Kesseldampf-/dT/dt-Verlauf.
  Prozessdynamik, EC 1 min und kompakter Nachlauf-Score/Alarm bleiben sichtbar;
  der Kühler ist keine Entscheidungsgröße für den State.
- **Temperatur – Prozessanalyse**, **EC Prozesssignal**, **Nachlauf-Detector**:
  nur operative Kurven. Keine Glättungs-/Trend-/CUSUM-Interna im Hauptbereich.

Die standardmäßig eingeklappte Row **Diagnose / Entwicklung** enthält:

- **Vergleichsmarker**: alle bisherigen Plateau-EC-Features, Trends, trend_accel,
  rise_from_min, dT/dt und Temperatur-/EC-Diagnosen bleiben sichtbar.
- **EC Glättung / Baseline**: raw_mv_1m, raw_mv_5m und Baseline-Mittelwert.
- **CUSUM Diagnose**: S, z, baseline_mu und baseline_sigma; bestehende
  CUSUM-Schwellen 4/8 und Diagnoseeinheiten bleiben erhalten.

Die Row **Rohdaten / Engineering** bewahrt die früheren Rohdaten-Gauges/-Kurven
und Engineering-Panels. Keine bestehenden Analysefeatures wurden entfernt.
Alle Analysepanels lesen process_analysis; Grafana berechnet weder Features
noch States. `50 * detector_score` bleibt reine Anzeigeformatierung: 50 ist
S=h und 100 ist S>=2h, keine Wahrscheinlichkeit. Die Anlage wird nicht gesteuert.

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
und die Unabhängigkeit von CUSUM/Alarm gegenüber Trendfeatures. Vorlauf-
Entscheidungen verwenden ausschließlich dT/dt-Dynamik; EC und Trendfeatures
bleiben diagnostisch.

Zusätzliche zeitbasierte Tests prüfen historische NULL-Run-Messungen vom
09.10.2026, automatisches Warmup, keine Persistenz außerhalb des Speicherfensters,
gezieltes Ersetzen einschließlich leerer Bereiche, Erhalt anderer Versionen,
Transaktions-Rollback und mehrere getrennte Brände mit Live-/Replay-Gleichheit.
Auch ein Teil-Rebuild nach über 30 Minuten übernimmt die ursprüngliche Baseline.
Temperaturdynamik-Tests prüfen vorherige Aufheizphase, persistenten Einbruch,
vollständiges Near-zero-Fenster, Median und Anteil als getrennte Bedingungen,
Ausreißertoleranz, weitere Bestätigung und deren Unterbrechung, Datenlücken,
MITTELLAUF-Verriegelung sowie gleiche Zustandsfolgen bei Plateau-Niveaus von
79/82/84 °C. EC, Trends und Recovery blockieren die Übergänge nicht.
Live und vollständiger/Teil-Rebuild speichern dieselben Zustände und EC-
Diagnosen; Rohdaten bleiben unverändert. CUSUM-Diagnosen und Scores sind trotz
unterschiedlicher Vorlauf-Freigabe identisch; h=8 und Hysterese bleiben erhalten.

Die vollständige Suite umfasst Backend- und Watchdogtests; das aktuelle Ergebnis
ist im Abschlussbericht dokumentiert. Ein gerendertes Grafana-UI und die echte
TimescaleDB-Laufzeit sind zusätzliche Integrationsprüfungen.

## I. Historische Plausibilitätsprüfung am 09.10.2026

Verwendet wurden die zwei bereitgestellten Grafana-CSV-Exporte
`Vergleichsmarker-data-2026-10-14 13_05_30.csv` und
`CUSUM Diagnose-data-2026-10-14 13_05_53.csv` mit je 1183 abgeschlossenen
20-s-Punkten von 12:55:40 bis 19:29:40. Zeitannahme: Europe/Berlin, UTC+02:00.

Dies ist ein **Export-Replay, kein vollständiger Rohdaten-Rebuild**: Die Dateien
enthalten gerundete Bucket-Mittel, keinen PT1000-Rohkanal, keine vollständigen
Qualitätsflags und keine Vorgeschichte vor Exportbeginn. Für das Replay wurde
der fehlende PT-Kanal als gültig angenommen; bestehende EC-Ungültigkeitsregeln
blieben aktiv. Weder sensor_measurements noch produktive Analysewerte wurden
mit Exportdaten befüllt. Ein echter Rebuild benötigt die originale Datenbank.

| Phase | Zwetschke | Birne |
|---|---|---|
| BEREIT vor Aufheizen | 12:55:40 (Initialannahme) | 15:46:00 |
| AUFHEIZEN | 12:59:00 | 15:56:20 |
| VORLAUF | 14:05:00 | 16:44:40 |
| VORLAUF_AUSKLANG | 14:06:00 | 16:46:20 |
| MITTELLAUF | 14:07:40 | 16:48:00 |
| NACHLAUF_ENTWICKELT | 14:55:20 | 17:45:40 |
| NACHLAUF | 14:58:00 | 17:50:00 |
| ABKÜHLEN | 15:14:00 | 18:32:00 |
| BEREIT danach | 15:46:00 | 18:51:40 |

Zusätzliche Qualitätsüberlagerungen im ersten Verlauf:
SENSOR_UNGUELTIG 13:37:40–13:50:40 und 15:21:00–15:42:40; danach Wiederaufnahme
der zuvor gehaltenen physischen Phase. Daher wird BEREIT nicht schon in einem
Fenster mit fehlender/ungültiger Sensorik bestätigt.

Der erste Aufheizbeginn ist besonders vorsichtig zu interpretieren: Der Export
beginnt bereits mit 34 °C und positivem Gradienten, danach folgt gegen 13:02 ein
starker Temperatursprung nach unten. Der CSV-Ausschnitt alleine beweist nicht,
ob die erste Bewegung schon zum Brand gehörte. Es wurde keine Sonderregel auf
bekannte Referenzzeiten gefittet. Bisherige Aufheiz-Anzeige im identischen
Export-Replay: 13:59:40 bzw. 16:40:20; die neue positive Dynamik wird früher
sichtbar. Vorlauf- und Nachlauf-Zeitpunkte bleiben in beiden Verläufen exakt
gleich. Die exportierten booleschen Alarme stimmen in allen 1183 Punkten mit
dem Replay überein. Im direkten Vergleich mit dem vorherigen Analyzer gibt es
keine Abweichung in CUSUM-Details, Score, Alarm oder internem ended-Flag.

### Kompatibilität und echter Rebuild

Migration 006 verwirft ausschließlich betroffene abgeleitete Detector-/Versions-
Serien, wenn sie noch alte IDLE-/ENDE-/NACHLAUF_WAHRSCHEINLICH-Zeilen enthalten.
Eine pauschale Umbenennung von ENDE wäre falsch, da daraus weder Abkühlung noch
Ruhezustand abgeleitet werden können. Rohdaten bleiben unverändert. Ohne alte
Zeilen ist ein erneuter Migrationslauf wirkungslos. Der unveränderte Worker
kann betroffene Serien anschließend aus der originalen Rohdaten-Historie neu
aufbauen. Vor Migration den alten Worker stoppen, aktualisierten Code und
Migrationen bereitstellen, danach den neuen Worker starten. Keine produktive
Migration in dieser Sitzung.

Für einen anschließenden echten Tages-Rebuild bei laufender Originaldatenbank:

```sh
curl --fail-with-body -X POST http://localhost:5000/api/analysis/rebuild \
  -H 'Content-Type: application/json' \
  -d '{"from":"2026-10-09T00:00:00+02:00","to":"2026-10-10T00:00:00+02:00","algo_version":"cusum-v1"}'
```

## J. Kontinuierliche Live-Verarbeitung

`docker-compose.yaml` startet genau einen `analysis-worker` mit
`python -m entrypoints.analysis_worker` im vorhandenen disti-backend-Image.
Er braucht nur Datenbankzugang, keinen Hardwarebus, keine API-Ports und keine
Queue. Die Hardware erfasst unverändert Rohdaten; API und Gunicorn bleiben
unverändert. Betriebsintervall: `DISTI_ANALYSIS_POLL_SECONDS=2` in disti.env,
Standard ebenfalls 2 s. Compose startet den Prozess nach einem Abbruch neu.

Start/Restart:

1. Letzten gespeicherten Analysezeitpunkt für Detector/Version lesen.
2. Einen neuen ProcessAnalyzer mit derselben Config wie der Rebuild erzeugen.
3. Verfügbare relevante Rohdaten bis einschließlich dieses letzten Buckets
   durch die bestehende Aggregation und update()-Logik abspielen, **ohne**
   vorhandene Analysezeilen zu löschen oder neu zu schreiben. Vollständige
   Vorgeschichte ist nötig, weil die eingefrorene Baseline/CUSUM nicht mit
   einem festen Warmup-Fenster exakt wiederhergestellt werden kann.
4. Nur fehlende Buckets nach diesem Zeitpunkt chronologisch nachholen; danach
   jedes neu abgeschlossene UTC-20-s-Intervall verarbeiten. Ohne vorhandene
   Analyse beim ersten relevanten Sensor-Bucket beginnen; ohne Rohdaten warten.

Der Worker hält Analyzer und nächsten Bucket im Speicher. Im laufenden Betrieb
ruft er für jeden abgeschlossenen Bucket genau einmal auf:

```python
service.process_completed_bucket(analyzer, bucket_start_utc)
```

Dafür wird nur dieser einzelne Bucket geladen. Auch leere Buckets werden mit
dem bestehenden Datenlückenstatus gespeichert. Der aktuelle offene Bucket
und Zukunftsdaten werden nicht ausgewertet. Bestehende Upserts mit
`(time, detector_name, algo_version)` verhindern doppelte Datensätze. Es gibt
keinen zweiten State-Store oder Analyzer-Checkpoint und keinen vollständigen
DB-Rebuild beim Start; die alte Vorgeschichte wird nur im Speicher aufgewärmt.

Bei einem temporären DB-Fehler loggt der Loop die Exception und wartet bis zum
nächsten Zyklus. Der Analyzer wird verworfen, weil update() vor dem fehlgeschlagenen
Save bereits gelaufen sein kann. Beim Retry wird er vom letzten tatsächlich
persistierten Punkt wiederhergestellt. Auch eine verlorene Bestätigung eines
bereits committed Saves verursacht keine Duplikate. Ungültige Sensorwerte
laufen durch die vorhandene Analyzer-Logik. SIGTERM/SIGINT stoppen die Schleife.

Verzögerung nach Bucket-Ende: normalerweise 0–2 s bis zur Persistenz; zusätzlich
bis zu 10 s Grafana-Refresh. Vom einzelnen Messwert aus kommt die restliche
Bucket-Dauer (bis zu 20 s) hinzu. Die Start-Aufwärmzeit hängt von der vorhandenen
Historie ab. Überlappende manuelle Rebuilds mit dem Worker serialisieren:

```sh
docker compose stop analysis-worker
# vorhandenen zeitbasierten Rebuild ausführen
docker compose up -d analysis-worker
```

Nach Bereitstellung des aktualisierten Images und Anwendung vorhandener Migrationen:

```sh
docker compose up -d --build --no-deps analysis-worker
docker compose logs --tail=100 analysis-worker
```

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
- Die experimentelle Vorlauf-/Mittellauf-Anzeige benötigt noch Validierung
  mit den beiden historischen Rohdatenverläufen.
- Dashboard-SQL wurde strukturell und zusätzlich soweit möglich gegen PostgreSQL
  geprüft; ein gerendertes Grafana-UI und echte TimescaleDB-Laufzeit sind getrennte
  Integrationsprüfungen.
