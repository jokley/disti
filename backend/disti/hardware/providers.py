"""Device-independent mock and replay sensor providers."""
from datetime import datetime, timezone
import math
import time

from .base import SensorReader, SensorReading

class MockSensorReader(SensorReader):
    """Deterministic warm-up, plateau and tails curves based on elapsed time."""
    def __init__(self, clock=time.monotonic):
        self.clock, self.started = clock, clock()

    def read(self):
        elapsed = self.clock() - self.started
        temperature = 20 + 58 * (1 - math.exp(-elapsed / 900)) + 0.6 * math.sin(elapsed / 90)
        raw_mv = 720 + 180 * math.exp(-((elapsed - 1800) / 900) ** 2) + 8 * math.sin(elapsed / 45)
        raw_count = round(raw_mv / 4096 * 32767)
        ec = max(0, (raw_mv - 400) * 0.003)
        stamp = datetime.now(timezone.utc)
        return [
            SensorReading("boiler-top", "temperature", round(temperature, 4), "degC", timestamp=stamp),
            SensorReading("ec-1", "ec", round(ec, 6), "mS/cm", timestamp=stamp,
                          raw_value=raw_count, raw_mv=round(raw_mv, 4), temperature=round(temperature, 4)),
        ]


class ReplaySensorReader(SensorReader):
    def __init__(self, repository, run_id, speed=1.0, preserve_timing=True, sleep=time.sleep):
        self.rows = iter(repository.replay_measurements(run_id))
        self.speed = max(float(speed), 0.001)
        self.preserve_timing = preserve_timing
        self.sleep = sleep
        self.previous_time = None

    def read(self):
        row = next(self.rows)
        recorded = datetime.fromisoformat(str(row["time"]).replace("Z", "+00:00"))
        if self.preserve_timing and self.previous_time:
            self.sleep(max(0, (recorded - self.previous_time).total_seconds()) / self.speed)
        self.previous_time = recorded
        return [SensorReading(row["sensor_id"], row["measurement_type"], row["value"], row["unit"],
                              raw_value=row.get("raw_value"), raw_mv=row.get("raw_mv"),
                              temperature=row.get("temperature"), calibration_id=row.get("calibration_id"),
                              quality=row.get("quality") or "good", metadata={"replay_source_time": recorded.isoformat()})]


