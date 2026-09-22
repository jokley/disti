from disti.api.app import create_app
import disti.api.app as app_module


def test_calibration_history_and_active_selection(repo):
    repo.ensure_sensor("ec-1", "EC", "ec")
    client = create_app(repo).test_client()
    first = client.post("/api/sensors/ec-1/calibration/start", json={}).get_json()
    point = client.post("/api/sensors/ec-1/calibration/point", json={"calibration_id":first["id"],"raw_mv":700,"raw_value":5600,"reference_value":1.413,"solution_temperature":25}).get_json()
    assert "reference_value" in point["points"]
    saved = client.post("/api/sensors/ec-1/calibration/save", json={"calibration_id":first["id"],"slope":0.002,"offset":0.1}).get_json()
    assert saved["offset"] == 0.1
    assert "calibration_offset" not in saved
    second = client.post("/api/sensors/ec-1/calibration/start", json={}).get_json()
    client.post("/api/sensors/ec-1/calibration/save", json={"calibration_id":second["id"],"activate":True})
    history = client.get("/api/sensors/ec-1/calibration").get_json()
    assert saved["active"] == 1
    assert sum(bool(item["active"]) for item in history) == 1


def test_finalized_calibration_data_is_immutable(repo):
    repo.ensure_sensor("ec-1", "EC", "ec")
    calibration = repo.start_calibration("ec-1", "linear")
    repo.add_calibration_point("ec-1", calibration["id"], {"raw_mv": 700, "reference_value": 1.413})
    repo.save_calibration("ec-1", calibration["id"], {"slope": 0.002, "calibration_offset": 0.1})
    try:
        repo.add_calibration_point("ec-1", calibration["id"], {"raw_mv": 800})
        assert False, "finalized calibration accepted a new point"
    except ValueError:
        pass


def test_initial_schema_uses_non_reserved_calibration_offset():
    from pathlib import Path

    sql = (Path(__file__).parents[2] / "migrations" / "001_modular_hardware.sql").read_text()
    assert "calibration_offset double precision" in sql
    assert " offset double precision" not in sql


def test_backend_health_checks_database(repo):
    response = create_app(repo).test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"database": "ok", "service": "backend", "status": "healthy"}
    assert create_app(repo).test_client().get("/healthz").get_json() == {"status": "ok"}


def test_watchdog_status_reports_database_and_hardware(repo, monkeypatch):
    requested = []
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def read(self): return b'{"status":"healthy","last_read_at":1}'
    monkeypatch.setenv("DISTI_HARDWARE_HEALTH_URL", "http://hardware-agent:8081")
    monkeypatch.setattr(app_module, "urlopen", lambda url, **kwargs: requested.append(url) or Response())
    payload = create_app(repo).test_client().get("/watchdog/status").get_json()
    assert payload["database"]["healthy"] is True
    assert payload["hardware_agent"]["healthy"] is True
    assert payload["status"] == "ok"
    assert requested == ["http://hardware-agent:8081/healthz"]


def test_run_and_fraction_lifecycle(repo):
    client = create_app(repo).test_client()
    run = client.post("/api/runs", json={"run_type":"gin","batch_name":"QA"}).get_json()
    assert client.get("/api/runs/active").get_json()["id"] == run["id"]
    fraction = client.post(f'/api/runs/{run["id"]}/fractions/start', json={"fraction_number":1,"fraction_type":"heads"}).get_json()
    ended = client.post(f'/api/runs/{run["id"]}/fractions/{fraction["id"]}/end').get_json()
    assert ended["ended_at"] is not None
    assert client.post(f'/api/runs/{run["id"]}/cuts', json={"note":"taste"}).status_code == 201
    assert client.post(f'/api/runs/{run["id"]}/stop').get_json()["status"] == "completed"
    assert client.get("/api/runs/active").status_code == 404
