from disti.mock_scenario import RUN_ID, build_mock_scenario
from seed_mock_run import seed


def test_complete_mock_scenario_is_repeatable():
    first, second = build_mock_scenario(), build_mock_scenario()
    assert first == second
    assert len(first["readings"]) == 182
    assert first["readings"][0].sensor_id == "boiler-top"
    ec = [reading for reading in first["readings"] if reading.sensor_id == "ec-1"]
    assert all(reading.raw_value is not None and reading.raw_mv is not None for reading in ec)
    assert all(reading.temperature is not None for reading in ec)
    assert ec[35].metadata["calculation"] == "placeholder"
    assert abs(ec[35].raw_mv - ec[55].raw_mv) < 6  # stable middle phase
    assert ec[-1].raw_mv < ec[70].raw_mv  # late-run EC decline
    marker_types = [marker.marker_type for marker in first["markers"]]
    assert "manual_cut" in marker_types
    assert "move_to_heart" in marker_types
    assert marker_types.count("fraction_start") == 3


def test_mock_scenario_seed_is_idempotent(repo):
    assert seed(repo) == RUN_ID
    assert seed(repo) == RUN_ID
    rows = repo.replay_measurements(RUN_ID)
    assert len(rows) == 182
    fractions = repo._execute("SELECT * FROM fractions WHERE run_id=%s ORDER BY started_at", (RUN_ID,))
    events = repo._execute("SELECT * FROM actuator_events WHERE run_id=%s ORDER BY time", (RUN_ID,))
    assert [item["fraction_type"] for item in fractions] == ["heads", "heart", "tails"]
    assert all(item["ended_at"] for item in fractions)
    assert any(item["event_type"] == "manual_cut" for item in events)
    assert sum(item["actuator_id"] == "fraction-collector" for item in events) == 4


def test_grafana_views_expose_values_derivatives_and_timeline():
    from pathlib import Path
    sql = (Path(__file__).parents[1] / "migrations" / "002_engineering_views.sql").read_text()
    for field in ("value_rate", "value_acceleration", "raw_value", "raw_mv", "temperature", "quality"):
        assert field in sql
    for source in ("sensor_measurements", "fractions", "actuator_events"):
        assert source in sql
