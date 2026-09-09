"""Hardware abstraction layer; business logic depends only on these protocols."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import os
from pathlib import Path
import time


@dataclass
class SensorReading:
    sensor_id: str
    measurement_type: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    raw_value: float | None = None
    raw_mv: float | None = None
    temperature: float | None = None
    calibration_id: str | None = None
    quality: str = "good"
    metadata: dict = field(default_factory=dict)


class SensorReader(ABC):
    @abstractmethod
    def read(self) -> list[SensorReading]: ...


class ADCReader(ABC):
    @abstractmethod
    def read_channel(self, channel: int) -> tuple[int, float]: ...


class TemperatureProvider(SensorReader): pass
class ECProvider(SensorReader): pass


class FractionCollector(ABC):
    @abstractmethod
    def home(self): ...
    @abstractmethod
    def move_to_position(self, position: int): ...
    @abstractmethod
    def move_to_heart(self): ...
    @abstractmethod
    def move_to_tails(self): ...
    @abstractmethod
    def next_sample(self): ...


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


class RaspberrySensorReader(SensorReader):
    """Configured Raspberry provider; ADS details remain behind ADCReader."""
    def __init__(self, adc=None, adc_factory=None):
        self.bus = int(os.getenv("DISTI_I2C_BUS", "1"))
        self.address = os.getenv("DISTI_ADS1115_ADDRESS", "0x48")
        self.channels = [
            ("ec-1", "ec", int(os.getenv("DISTI_ADS1115_EC_CHANNEL", "0"))),
            ("ec-temp", "temperature", int(os.getenv("DISTI_ADS1115_PT1000_CHANNEL", "1"))),
        ]
        if os.getenv("DISTI_ADC_TYPE", "ads1115").lower() != "ads1115":
            raise ValueError("unsupported DISTI_ADC_TYPE (expected ads1115)")
        self._factory = adc_factory
        self.adc = adc
        self.last_successful_read = None
        self.last_error = None
        if self.adc is None:
            try:
                self._initialize_adc()
            except Exception as exc:
                self.last_error = str(exc)

    def _initialize_adc(self):
        if self._factory is None:
            from .ads1115 import ADS1115Reader
            self._factory = ADS1115Reader
        self.adc = self._factory(bus=self.bus, address=self.address,
                                 gain=float(os.getenv("DISTI_ADS1115_GAIN", "1")),
                                 data_rate=int(os.getenv("DISTI_ADS1115_DATA_RATE", "128")))

    def read(self):
        if self.adc is None:
            self._initialize_adc()
        readings = []
        try:
            stamp = datetime.now(timezone.utc)
            for sensor_id, measurement_type, channel in self.channels:
                sample = self.adc.read_channel(channel)
                readings.append(SensorReading(
                    sensor_id, measurement_type, sample.raw_mv, "mV", timestamp=stamp,
                    raw_value=sample.raw_count, raw_mv=sample.raw_mv,
                    metadata={"adc_type": "ads1115", "channel": channel,
                              "engineering_conversion": "not_configured"}))
            self.last_successful_read, self.last_error = stamp, None
            return readings
        except Exception as exc:
            self.last_error = str(exc)
            raise

    def health(self):
        return {
            "mode": "raspberry",
            "i2c_available": self.adc is not None or Path(f"/dev/i2c-{self.bus}").exists(),
            "ads1115_reachable": bool(self.adc and getattr(self.adc, "reachable", True)),
            "acquisition_running": self.last_successful_read is not None,
            "last_successful_read": self.last_successful_read.isoformat() if self.last_successful_read else None,
            "last_error": self.last_error,
        }


class MockFractionCollector(FractionCollector):
    def __init__(self, repository): self.repository, self.position = repository, 0
    def _move(self, command, position):
        self.position = position
        return self.repository.record_event(command, {"position": position}, actuator_id="fraction-collector")
    def home(self): return self._move("home", 0)
    def move_to_position(self, position): return self._move("move_to_position", int(position))
    def move_to_heart(self): return self._move("move_to_heart", "heart")
    def move_to_tails(self): return self._move("move_to_tails", "tails")
    def next_sample(self): return self.move_to_position(int(self.position) + 1)


class HardwareManager:
    def __init__(self, readers, collector=None): self.readers, self.collector = readers, collector
    def read_all(self):
        return [reading for reader in self.readers for reading in reader.read()]
