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
        return cls(lambda: psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "postgres"),
            user=os.getenv("DOCKER_POSTGRES_INIT_USERNAME", "postgres"),
            password=os.getenv("DOCKER_POSTGRES_INIT_PASSWORD", "postgres")))

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
                          data.get("offset", calibration.get("offset")) != calibration.get("offset")):
            raise ValueError("finalized calibration coefficients are immutable")
        if activate:
            self._execute("UPDATE sensor_calibrations SET active=%s WHERE sensor_id=%s", (False, sensor_id), fetch=None)
        if not finalized:
            self._execute("UPDATE sensor_calibrations SET slope=%s, offset=%s, finalized_at=%s WHERE id=%s",
                          (data.get("slope"), data.get("offset"), now().isoformat(), calibration_id), fetch=None)
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
