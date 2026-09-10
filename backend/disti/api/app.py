"""DISTI Flask application.

The web process exposes control APIs only. Continuous acquisition lives in
``entrypoints.hardware_agent`` so restarting gunicorn never interrupts measurements.
"""
from datetime import datetime, timezone
import os
import json as json_module
from urllib.request import urlopen

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from disti.repository import Repository


def _json(row):
    if row is None:
        return None
    return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}


def _calibration_json(row):
    """Expose the established API name without leaking the database column name."""
    result = _json(row)
    if result is not None and "calibration_offset" in result:
        result["offset"] = result.pop("calibration_offset")
    return result


def create_app(repository=None):
    app = Flask(__name__)
    CORS(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    repo = repository or Repository.from_environment()
    app.extensions["disti_repository"] = repo

    @app.get("/")
    def index():
        return jsonify(service="disti-backend", status="ok")

    @app.get("/health")
    def health():
        return jsonify(service="backend", status="healthy", database=repo.ping())

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/watchdog/status")
    def watchdog_status():
        threshold = float(os.getenv("DISTI_HARDWARE_MAX_AGE_SEC", "30"))
        result = {"status": "ok", "database": {"healthy": False},
                  "hardware_agent": {"healthy": False}, "measurement_freshness": None, "reason": None}
        try:
            repo.ping()
            result["database"] = {"healthy": True}
            freshness = repo.measurement_freshness()
            freshness["threshold_seconds"] = threshold
            result["measurement_freshness"] = freshness
        except Exception as exc:
            result.update(status="degraded", reason=f"database: {exc}")
        try:
            health_url = os.getenv("DISTI_HARDWARE_HEALTH_URL", "http://hardware-agent:8081").rstrip("/")
            if not health_url.endswith("/healthz"):
                health_url += "/healthz"
            with urlopen(health_url, timeout=5) as response:
                agent = json_module.load(response)
            agent["healthy"] = agent.get("status") in ("healthy", "replay-complete")
            result["hardware_agent"] = agent
            age = result["measurement_freshness"] and result["measurement_freshness"]["youngest_age_seconds"]
            if not agent["healthy"] or (age is not None and age > threshold):
                result.update(status="degraded", reason="hardware-agent unhealthy or measurements stale")
        except Exception as exc:
            result.update(status="degraded", reason=f"hardware-agent: {exc}")
        return jsonify(result), 200

    @app.get("/api/sensors")
    def sensors():
        return jsonify([_json(row) for row in repo.list_sensors()])

    @app.get("/api/sensors/<sensor_id>")
    def sensor(sensor_id):
        row = repo.get_sensor(sensor_id)
        return (jsonify(_json(row)), 200) if row else (jsonify(error="sensor not found"), 404)

    @app.get("/api/sensors/<sensor_id>/calibration")
    def calibrations(sensor_id):
        return jsonify([_calibration_json(row) for row in repo.list_calibrations(sensor_id)])

    @app.post("/api/sensors/<sensor_id>/calibration/start")
    def calibration_start(sensor_id):
        row = repo.start_calibration(sensor_id, (request.get_json(silent=True) or {}).get("model", "linear"))
        return jsonify(_calibration_json(row)), 201

    @app.post("/api/sensors/<sensor_id>/calibration/point")
    def calibration_point(sensor_id):
        data = request.get_json(force=True)
        row = repo.add_calibration_point(sensor_id, data["calibration_id"], data)
        return jsonify(_calibration_json(row)), 201

    @app.post("/api/sensors/<sensor_id>/calibration/save")
    def calibration_save(sensor_id):
        data = request.get_json(force=True)
        # ``offset`` is the public API contract; the persistence boundary uses
        # the non-reserved, explicit ``calibration_offset`` name.
        if "offset" in data:
            data["calibration_offset"] = data.pop("offset")
        row = repo.save_calibration(sensor_id, data["calibration_id"], data, data.get("activate", True))
        return jsonify(_calibration_json(row))

    @app.post("/api/runs")
    def start_run():
        return jsonify(_json(repo.start_run(request.get_json(silent=True) or {}))), 201

    @app.get("/api/runs/active")
    def active_run():
        row = repo.active_run()
        return (jsonify(_json(row)), 200) if row else (jsonify(error="no active run"), 404)

    @app.post("/api/runs/<run_id>/stop")
    def stop_run(run_id):
        return jsonify(_json(repo.stop_run(run_id)))

    @app.post("/api/runs/<run_id>/fractions/start")
    def fraction_start(run_id):
        return jsonify(_json(repo.start_fraction(run_id, request.get_json(silent=True) or {}))), 201

    @app.post("/api/runs/<run_id>/fractions/<fraction_id>/end")
    def fraction_end(run_id, fraction_id):
        return jsonify(_json(repo.end_fraction(run_id, fraction_id)))

    @app.post("/api/runs/<run_id>/cuts")
    def manual_cut(run_id):
        data = request.get_json(silent=True) or {}
        return jsonify(_json(repo.record_event("manual_cut", data, run_id=run_id))), 201

    @app.get("/api/version")
    def version():
        return jsonify(version=os.getenv("DISTI_VERSION", "development"),
                       build=os.getenv("DISTI_BUILD", "local"),
                       update_channel=os.getenv("DISTI_UPDATE_BRANCH", "dev"))

    return app
