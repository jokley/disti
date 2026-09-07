from datetime import datetime, timezone

from disti.hardware import MockFractionCollector, MockSensorReader, ReplaySensorReader
from hardware_agent import Agent


def test_mock_data_is_deterministic_and_keeps_ec_raw_values():
    clock = lambda: 900.0
    readings = MockSensorReader(clock).read()
    assert readings[0].value == 20.0
    assert readings[1].raw_value is not None
    assert readings[1].raw_mv is not None
    assert readings[1].temperature == readings[0].value


def test_replay_preserves_order_and_scales_timing():
    class Source:
        def replay_measurements(self, _):
            base = {"sensor_id":"ec-1","measurement_type":"ec","value":1.2,"unit":"mS/cm","raw_value":10,"raw_mv":20,"temperature":30,"calibration_id":None,"quality":"good"}
            return [dict(base,time="2025-01-01T00:00:00+00:00"), dict(base,time="2025-01-01T00:00:10+00:00",value=1.3)]
    sleeps=[]; replay=ReplaySensorReader(Source(), "run", speed=2, sleep=sleeps.append)
    assert replay.read()[0].value == 1.2
    assert replay.read()[0].value == 1.3
    assert sleeps == [5]


def test_agent_restart_appends_to_active_run(repo):
    run = repo.start_run({})
    Agent(repo, MockSensorReader(lambda: 0), interval=1).poll_once()
    Agent(repo, MockSensorReader(lambda: 0), interval=1).poll_once()
    rows = repo.replay_measurements(run["id"])
    assert len(rows) == 4
    assert all(row["run_id"] == run["id"] for row in rows)


def test_fraction_collector_persists_actuator_event(repo):
    event = MockFractionCollector(repo).move_to_position(3)
    assert event["event_type"] == "move_to_position"
    assert '"position": 3' in event["details"]
