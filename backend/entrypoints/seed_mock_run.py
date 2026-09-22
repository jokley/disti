"""Persist the deterministic Grafana scenario. Refuses to overwrite any run."""
import json
from datetime import timedelta
from uuid import NAMESPACE_URL, uuid5

from disti.mock_scenario import build_mock_scenario
from disti.repository import Repository


def seed(repository=None):
    repo = repository or Repository.from_environment()
    scenario = build_mock_scenario()
    existing = repo._execute("SELECT id FROM distillation_runs WHERE id=%s", (scenario["id"],), "one")
    if existing:
        return scenario["id"]
    repo.ensure_sensor("boiler-top", "BoilerTop", "temperature")
    repo.ensure_sensor("ec-1", "EC", "ec")
    repo._execute("INSERT INTO distillation_runs(id,run_type,batch_name,notes,status,started_at,ended_at) VALUES(%s,'other',%s,%s,'completed',%s,%s)",
                  (scenario["id"], scenario["name"], "Repeatable Grafana development fixture",
                   scenario["started_at"].isoformat(), scenario["ended_at"].isoformat()), fetch=None)
    for reading in scenario["readings"]:
        repo.save_measurement(reading, scenario["id"])
    active_fraction = None
    for marker in scenario["markers"]:
        timestamp = scenario["started_at"] + timedelta(minutes=marker.minute)
        if marker.marker_type == "fraction_start":
            if active_fraction:
                repo._execute("UPDATE fractions SET ended_at=%s WHERE id=%s", (timestamp.isoformat(), active_fraction), fetch=None)
            active_fraction = str(uuid5(NAMESPACE_URL, f'{scenario["name"]}:fraction:{marker.details["fraction_number"]}'))
            repo._execute("INSERT INTO fractions(id,run_id,fraction_number,fraction_type,started_at) VALUES(%s,%s,%s,%s,%s)",
                          (active_fraction, scenario["id"], marker.details["fraction_number"], marker.details["fraction_type"], timestamp.isoformat()), fetch=None)
        elif marker.marker_type != "run_stop":
            repo.record_event(marker.marker_type, marker.details, run_id=scenario["id"],
                              actuator_id="fraction-collector" if marker.marker_type != "manual_cut" else None,
                              timestamp=timestamp,
                              event_id=str(uuid5(NAMESPACE_URL, f'{scenario["name"]}:event:{marker.minute}:{marker.marker_type}')))
    if active_fraction:
        repo._execute("UPDATE fractions SET ended_at=%s WHERE id=%s", (scenario["ended_at"].isoformat(), active_fraction), fetch=None)
    return scenario["id"]


if __name__ == "__main__":
    print(json.dumps({"run_id": seed()}))
