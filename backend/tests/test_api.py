from app import create_app


def test_calibration_history_and_active_selection(repo):
    repo.ensure_sensor("ec-1", "EC", "ec")
    client = create_app(repo).test_client()
    first = client.post("/api/sensors/ec-1/calibration/start", json={}).get_json()
    point = client.post("/api/sensors/ec-1/calibration/point", json={"calibration_id":first["id"],"raw_mv":700,"raw_value":5600,"reference_value":1.413,"solution_temperature":25}).get_json()
    assert "reference_value" in point["points"]
    saved = client.post("/api/sensors/ec-1/calibration/save", json={"calibration_id":first["id"],"slope":0.002,"offset":0.1}).get_json()
    second = client.post("/api/sensors/ec-1/calibration/start", json={}).get_json()
    client.post("/api/sensors/ec-1/calibration/save", json={"calibration_id":second["id"],"activate":True})
    history = client.get("/api/sensors/ec-1/calibration").get_json()
    assert saved["active"] == 1
    assert sum(bool(item["active"]) for item in history) == 1


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
