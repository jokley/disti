"""DISTI Flask application.

The web process exposes control APIs only. Continuous acquisition lives in
``hardware_agent.py`` so restarting gunicorn never interrupts measurements.
"""
from datetime import datetime, timezone
import os

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from disti.repository import Repository


def _json(row):
    if row is None:
        return None
    return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in row.items()}


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

    @app.get("/api/sensors")
    def sensors():
        return jsonify([_json(row) for row in repo.list_sensors()])

    @app.get("/api/sensors/<sensor_id>")
    def sensor(sensor_id):
        row = repo.get_sensor(sensor_id)
        return (jsonify(_json(row)), 200) if row else (jsonify(error="sensor not found"), 404)

    @app.get("/api/sensors/<sensor_id>/calibration")
    def calibrations(sensor_id):
        return jsonify([_json(row) for row in repo.list_calibrations(sensor_id)])

    @app.post("/api/sensors/<sensor_id>/calibration/start")
    def calibration_start(sensor_id):
        row = repo.start_calibration(sensor_id, (request.get_json(silent=True) or {}).get("model", "linear"))
        return jsonify(_json(row)), 201

    @app.post("/api/sensors/<sensor_id>/calibration/point")
    def calibration_point(sensor_id):
        data = request.get_json(force=True)
        row = repo.add_calibration_point(sensor_id, data["calibration_id"], data)
        return jsonify(_json(row)), 201

    @app.post("/api/sensors/<sensor_id>/calibration/save")
    def calibration_save(sensor_id):
        data = request.get_json(force=True)
        row = repo.save_calibration(sensor_id, data["calibration_id"], data, data.get("activate", True))
        return jsonify(_json(row))

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


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
