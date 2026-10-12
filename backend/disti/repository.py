"""Small persistence boundary shared by Flask and the hardware agent."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import psycopg2
import psycopg2.extras


def now():
    return datetime.now(timezone.utc)


class Repository:
    def __init__(self, connection_factory, sqlite=False):
        self.connection_factory = connection_factory
        self.sqlite = sqlite

    @classmethod
    def from_environment(cls):
        url = os.getenv("DATABASE_URL")
        if url and url.startswith("sqlite:///"):
            path = url.removeprefix("sqlite:///")
            return cls(lambda: sqlite3.connect(path), sqlite=True)
        required_names = (
            "POSTGRES_HOST",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
        )
        missing = [name for name in required_names if not os.environ.get(name)]
        if missing:
            raise RuntimeError(
                "Missing required PostgreSQL configuration: " + ", ".join(missing)
            )
        return cls(lambda: psycopg2.connect(
            host=os.environ["POSTGRES_HOST"],
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"]))

    def _execute(self, sql, params=(), fetch="all"):
        conn = self.connection_factory()
        if self.sqlite:
            conn.row_factory = sqlite3.Row
            sql = sql.replace("%s", "?")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if not self.sqlite else conn.cursor()
        try:
            cur.execute(sql, params)
            result = cur.fetchone() if fetch == "one" else cur.fetchall() if fetch == "all" else None
            conn.commit()
            if result is None:
                return None
            if fetch == "one":
                return dict(result)
            return [dict(row) for row in result]
        finally:
            cur.close(); conn.close()

    def ping(self):
        self._execute("SELECT 1", fetch="one")
        return "ok"

    def measurement_freshness(self):
        row = self._execute("SELECT COUNT(*) AS sensor_count, MAX(time) AS newest_time, MIN(time) AS oldest_time FROM sensor_measurements", fetch="one")
        current = now()
        def age(value):
            if value is None:
                return None
            parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return max(0, (current - parsed).total_seconds())
        return {"sensor_count": row["sensor_count"], "youngest_age_seconds": age(row["newest_time"]),
                "oldest_age_seconds": age(row["oldest_time"])}

    def list_sensors(self): return self._execute("SELECT * FROM sensors ORDER BY name")
    def get_sensor(self, sensor_id): return self._execute("SELECT * FROM sensors WHERE id=%s", (sensor_id,), "one")
    def ensure_sensor(self, sensor_id, name, kind):
        if self.sqlite:
            sql = "INSERT OR IGNORE INTO sensors(id,name,sensor_type,enabled) VALUES(%s,%s,%s,1)"
        else:
            sql = "INSERT INTO sensors(id,name,sensor_type,enabled) VALUES(%s,%s,%s,true) ON CONFLICT(id) DO NOTHING"
        self._execute(sql, (sensor_id, name, kind), fetch=None)

    def list_calibrations(self, sensor_id):
        return self._execute("SELECT * FROM sensor_calibrations WHERE sensor_id=%s ORDER BY created_at DESC", (sensor_id,))

    def start_calibration(self, sensor_id, model):
        cid = str(uuid4()); created = now().isoformat()
        self._execute("INSERT INTO sensor_calibrations(id,sensor_id,version,model,points,active,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                      (cid, sensor_id, created, model, "[]", False, created), fetch=None)
        return self._execute("SELECT * FROM sensor_calibrations WHERE id=%s", (cid,), "one")

    def add_calibration_point(self, sensor_id, calibration_id, point):
        calibration = self._execute("SELECT * FROM sensor_calibrations WHERE id=%s AND sensor_id=%s", (calibration_id, sensor_id), "one")
        if not calibration: raise ValueError("calibration not found")
        if calibration.get("finalized_at"):
            raise ValueError("finalized calibrations are immutable")
        points = calibration["points"] if isinstance(calibration["points"], list) else json.loads(calibration["points"])
        points.append({key: point.get(key) for key in ("raw_value", "raw_mv", "reference_value", "solution_temperature", "timestamp")})
        self._execute("UPDATE sensor_calibrations SET points=%s WHERE id=%s", (json.dumps(points), calibration_id), fetch=None)
        return self._execute("SELECT * FROM sensor_calibrations WHERE id=%s", (calibration_id,), "one")

    def save_calibration(self, sensor_id, calibration_id, data, activate=True):
        calibration = self._execute("SELECT * FROM sensor_calibrations WHERE id=%s AND sensor_id=%s", (calibration_id, sensor_id), "one")
        if not calibration:
            raise ValueError("calibration not found")
        finalized = calibration.get("finalized_at")
        if finalized and (data.get("slope", calibration.get("slope")) != calibration.get("slope") or
                          data.get("calibration_offset", calibration.get("calibration_offset")) != calibration.get("calibration_offset")):
            raise ValueError("finalized calibration coefficients are immutable")
        if activate:
            self._execute("UPDATE sensor_calibrations SET active=%s WHERE sensor_id=%s", (False, sensor_id), fetch=None)
        if not finalized:
            self._execute("UPDATE sensor_calibrations SET slope=%s, calibration_offset=%s, finalized_at=%s WHERE id=%s",
                          (data.get("slope"), data.get("calibration_offset"), now().isoformat(), calibration_id), fetch=None)
        self._execute("UPDATE sensor_calibrations SET active=%s, activated_at=%s WHERE id=%s",
                      (activate, now().isoformat() if activate else None, calibration_id), fetch=None)
        return self._execute("SELECT * FROM sensor_calibrations WHERE id=%s", (calibration_id,), "one")

    def active_run(self): return self._execute("SELECT * FROM distillation_runs WHERE status='active' ORDER BY started_at DESC LIMIT 1", fetch="one")
    def start_run(self, data):
        if self.active_run(): raise ValueError("a run is already active")
        rid = str(uuid4())
        self._execute("INSERT INTO distillation_runs(id,run_type,recipe_name,batch_name,notes,status,started_at) VALUES(%s,%s,%s,%s,%s,'active',%s)",
                      (rid, data.get("run_type", "other"), data.get("recipe_name"), data.get("batch_name"), data.get("notes"), now().isoformat()), fetch=None)
        return self.active_run()
    def stop_run(self, run_id):
        self._execute("UPDATE fractions SET ended_at=%s WHERE run_id=%s AND ended_at IS NULL", (now().isoformat(), run_id), fetch=None)
        self._execute("UPDATE distillation_runs SET status='completed',ended_at=%s WHERE id=%s AND status='active'", (now().isoformat(), run_id), fetch=None)
        return self._execute("SELECT * FROM distillation_runs WHERE id=%s", (run_id,), "one")
    def start_fraction(self, run_id, data):
        self._execute("UPDATE fractions SET ended_at=%s WHERE run_id=%s AND ended_at IS NULL", (now().isoformat(), run_id), fetch=None)
        fid = str(uuid4())
        self._execute("INSERT INTO fractions(id,run_id,fraction_number,fraction_type,operator_notes,started_at) VALUES(%s,%s,%s,%s,%s,%s)",
                      (fid, run_id, data.get("fraction_number"), data.get("fraction_type"), data.get("operator_notes"), now().isoformat()), fetch=None)
        return self._execute("SELECT * FROM fractions WHERE id=%s", (fid,), "one")
    def end_fraction(self, run_id, fraction_id):
        self._execute("UPDATE fractions SET ended_at=%s WHERE id=%s AND run_id=%s", (now().isoformat(), fraction_id, run_id), fetch=None)
        return self._execute("SELECT * FROM fractions WHERE id=%s", (fraction_id,), "one")

    def save_measurement(self, reading, run_id=None):
        mid = str(uuid4())
        self._execute("INSERT INTO sensor_measurements(id,time,run_id,sensor_id,measurement_type,raw_value,raw_mv,value,unit,temperature,calibration_id,quality,metadata) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
          (mid, reading.timestamp.isoformat(), run_id, reading.sensor_id, reading.measurement_type, reading.raw_value, reading.raw_mv, reading.value, reading.unit, reading.temperature, reading.calibration_id, reading.quality, json.dumps(reading.metadata)), fetch=None)
        return mid
    def replay_measurements(self, run_id):
        return self._execute("SELECT * FROM sensor_measurements WHERE run_id=%s ORDER BY time", (run_id,))
    def record_event(self, event_type, details, run_id=None, actuator_id=None, timestamp=None, event_id=None):
        eid = event_id or str(uuid4())
        self._execute("INSERT INTO actuator_events(id,time,run_id,actuator_id,event_type,status,details) VALUES(%s,%s,%s,%s,%s,'completed',%s)",
                      (eid, (timestamp or now()).isoformat(), run_id, actuator_id, event_type, json.dumps(details)), fetch=None)
        return self._execute("SELECT * FROM actuator_events WHERE id=%s", (eid,), "one")

    def analysis_runs(self, start, end, run_id=None):
        if run_id is not None:
            return self._execute("SELECT id, ended_at FROM distillation_runs WHERE id=%s", (run_id,))
        return self._execute(
            "SELECT DISTINCT r.id, r.ended_at FROM distillation_runs r "
            "JOIN sensor_measurements m ON m.run_id=r.id "
            "WHERE m.time >= %s AND m.time < %s ORDER BY r.id",
            (start.isoformat(), end.isoformat()))

    def analysis_buckets(self, run_id, end, seconds, valid_qualities=('good', 'simulated'), start=None):
        # Aggregation only. Features and all process formulas live in process_analysis.
        lower_bound = ' AND time >= %s' if start is not None else ''
        lower_params = (start.isoformat(),) if start is not None else ()
        if not self.sqlite:
            return self._execute("""
                SELECT time_bucket(%s::interval, time) AS time,
                  avg(value) FILTER (WHERE sensor_id='vapor-temp') AS vapor_temp,
                  avg(raw_mv) FILTER (WHERE sensor_id='ec-1') AS raw_mv,
                  avg(raw_mv) FILTER (WHERE sensor_id='ec-temp') AS pt_raw_mv,
                  bool_or(quality IS NULL OR NOT (quality = ANY(%s))) AS sensor_invalid
                FROM sensor_measurements
                WHERE run_id=%s AND time < %s
                  AND sensor_id IN ('vapor-temp','ec-1','ec-temp')
                """ + lower_bound + ' GROUP BY 1 ORDER BY 1',
                (f'{seconds} seconds', list(valid_qualities), run_id, end.isoformat()) + lower_params)
        from collections import defaultdict
        from statistics import fmean
        from disti.process_analysis.service import timestamp, floor_bucket
        rows = self._execute("SELECT time,sensor_id,value,raw_mv,quality FROM sensor_measurements "
                             "WHERE run_id=%s AND time < %s AND sensor_id IN ('vapor-temp','ec-1','ec-temp')" + lower_bound + ' ORDER BY time',
                             (run_id, end.isoformat()) + lower_params)
        groups = defaultdict(list)
        for row in rows:
            groups[floor_bucket(timestamp(row['time']), seconds)].append(row)
        result = []
        for time, readings in sorted(groups.items()):
            item = {'time': time, 'sensor_invalid': any(r['quality'] not in valid_qualities for r in readings)}
            for sensor, field, source in (('vapor-temp','vapor_temp','value'), ('ec-1','raw_mv','raw_mv'), ('ec-temp','pt_raw_mv','raw_mv')):
                values = [r[source] for r in readings if r['sensor_id'] == sensor and r[source] is not None]
                item[field] = fmean(values) if values else None
            result.append(item)
        return result

    def save_analysis(self, results):
        """Atomic batch upsert, including corrections on repeated historical rebuilds."""
        from dataclasses import asdict
        if not results:
            return
        rows = []
        for result in results:
            row = asdict(result)
            row.update(row.pop('features'))
            row['time'] = result.time.isoformat()
            row['process_state'] = result.process_state.value
            row['details'] = json.dumps(row['details'], allow_nan=False)
            rows.append(row)
        columns = list(rows[0])
        placeholders = ','.join(['?' if self.sqlite else '%s']*len(columns))
        updates = ','.join(f'{col}=excluded.{col}' for col in columns if col not in ('run_id','time','detector_name','algo_version'))
        sql = f"INSERT INTO process_analysis ({','.join(columns)}) VALUES ({placeholders}) ON CONFLICT(run_id,time,detector_name,algo_version) DO UPDATE SET {updates}"
        conn = self.connection_factory()
        try:
            with conn:
                cur = conn.cursor()
                try:
                    cur.executemany(sql, [tuple(row[col] for col in columns) for row in rows])
                finally:
                    cur.close()
        finally:
            conn.close()
