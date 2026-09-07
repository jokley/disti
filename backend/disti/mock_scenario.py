"""Repeatable complete distillation scenario for API and Grafana development."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from uuid import NAMESPACE_URL, uuid5

from .hardware import SensorReading


SCENARIO_NAME = "DISTI deterministic Grafana run v1"
RUN_ID = str(uuid5(NAMESPACE_URL, SCENARIO_NAME))
START = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ScenarioMarker:
    minute: int
    marker_type: str
    details: dict


def build_mock_scenario():
    """Return the same 91-minute run on every invocation.

    The run contains heat-up, a stable hearts plateau, and a late-run
    temperature rise/EC decline. One-minute sampling makes derivative views
    useful without producing an unnecessarily large development fixture.
    """
    readings = []
    for minute in range(91):
        if minute < 30:
            temperature = 20 + 58.2 * (1 - math.exp(-minute / 7.5))
            ec_raw_mv = 540 + 8.5 * minute
        elif minute < 70:
            temperature = 78.2 + 0.08 * math.sin((minute - 30) / 4)
            ec_raw_mv = 795 + 2.5 * math.sin((minute - 30) / 5)
        else:
            temperature = 78.2 + 0.42 * (minute - 70)
            ec_raw_mv = 795 - 11.5 * (minute - 70)
        sensor_temperature = temperature - 0.35
        raw_count = round(ec_raw_mv / 4096 * 32767)
        calibrated_placeholder = max(0, (ec_raw_mv - 400) * 0.003)
        timestamp = START + timedelta(minutes=minute)
        readings.extend([
            SensorReading("boiler-top", "temperature", round(temperature, 4), "degC", timestamp=timestamp),
            SensorReading("ec-1", "ec", round(calibrated_placeholder, 6), "mS/cm", timestamp=timestamp,
                          raw_value=raw_count, raw_mv=round(ec_raw_mv, 4),
                          temperature=round(sensor_temperature, 4), quality="simulated",
                          metadata={"scenario": SCENARIO_NAME, "calculation": "placeholder"}),
        ])
    markers = [
        ScenarioMarker(0, "fraction_start", {"fraction_number": 1, "fraction_type": "heads"}),
        ScenarioMarker(0, "home", {"position": 0}),
        ScenarioMarker(1, "move_to_position", {"position": 1}),
        ScenarioMarker(30, "fraction_start", {"fraction_number": 2, "fraction_type": "heart"}),
        ScenarioMarker(30, "manual_cut", {"cut": "HEART", "note": "deterministic scenario marker"}),
        ScenarioMarker(30, "move_to_heart", {"position": "heart"}),
        ScenarioMarker(70, "fraction_start", {"fraction_number": 3, "fraction_type": "tails"}),
        ScenarioMarker(70, "move_to_tails", {"position": "tails"}),
        ScenarioMarker(90, "run_stop", {}),
    ]
    return {"id": RUN_ID, "name": SCENARIO_NAME, "started_at": START,
            "ended_at": START + timedelta(minutes=90), "readings": readings, "markers": markers}
