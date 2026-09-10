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


class OneWireReader(ABC):
    """Technology-neutral access to ROM-addressed 1-Wire thermometers."""
    @property
    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def discover(self) -> list[str]: ...

    @abstractmethod
    def read_temperature(self, rom_id: str) -> float: ...


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
    """Configured Raspberry provider; bus protocols remain behind readers."""
    def __init__(self, adc=None, adc_factory=None, onewire=None, onewire_factory=None):
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
        self.onewire_type = os.getenv("DISTI_ONEWIRE_TYPE", "disabled").lower()
        if self.onewire_type not in ("disabled", "ds2482"):
            raise ValueError("unsupported DISTI_ONEWIRE_TYPE (expected ds2482 or disabled)")
        self.onewire_enabled = self.onewire_type == "ds2482"
        self._onewire_factory = onewire_factory
        self.onewire = onewire
        self.onewire_bus = int(os.getenv("DISTI_DS2482_I2C_BUS", str(self.bus)))
        self.onewire_address = os.getenv("DISTI_DS2482_ADDRESS", "0x18")
        self.onewire_assignments = {
            "vapor-temp": os.getenv("DISTI_ONEWIRE_VAPOR_ID", "").strip().lower(),
            "cooler-temp": os.getenv("DISTI_ONEWIRE_COOLER_ID", "").strip().lower(),
            "reserve-temp": os.getenv("DISTI_ONEWIRE_RESERVE_ID", "").strip().lower(),
        }
        self.discovered_onewire = []
        self.last_successful_onewire_read = None
        self.onewire_last_error = None
        self.last_successful_read = None
        self.last_error = None
        if self.adc is None:
            try:
                self._initialize_adc()
            except Exception as exc:
                self.last_error = str(exc)
        if self.onewire_enabled and self.onewire is None:
            try:
                self._initialize_onewire()
            except Exception as exc:
                self.onewire_last_error = str(exc)

    def _initialize_adc(self):
        if self._factory is None:
            from .ads1115 import ADS1115Reader
            self._factory = ADS1115Reader
        self.adc = self._factory(bus=self.bus, address=self.address,
                                 gain=float(os.getenv("DISTI_ADS1115_GAIN", "1")),
                                 data_rate=int(os.getenv("DISTI_ADS1115_DATA_RATE", "128")))

    def _initialize_onewire(self):
        if self._onewire_factory is None:
            from .ds2482 import DS2482OneWireReader
            self._onewire_factory = DS2482OneWireReader
        self.onewire = self._onewire_factory(bus=self.onewire_bus, address=self.onewire_address)

    def read(self):
        readings = []
        errors = []
        adc_exception = None
        stamp = datetime.now(timezone.utc)
        try:
            if self.adc is None:
                self._initialize_adc()
            for sensor_id, measurement_type, channel in self.channels:
                sample = self.adc.read_channel(channel)
                readings.append(SensorReading(
                    sensor_id, measurement_type, sample.raw_mv, "mV", timestamp=stamp,
                    raw_value=sample.raw_count, raw_mv=sample.raw_mv,
                    metadata={"adc_type": "ads1115", "channel": channel,
                              "engineering_conversion": "not_configured"}))
            self.last_successful_read, self.last_error = stamp, None
        except Exception as exc:
            adc_exception = exc
            self.last_error = str(exc)
            errors.append(self.last_error)

        if self.onewire_enabled:
            try:
                if self.onewire is None:
                    self._initialize_onewire()
                self.discovered_onewire = self.onewire.discover()
                assigned = {rom for rom in self.onewire_assignments.values() if rom}
                present = set(self.discovered_onewire)
                readable = {name: rom for name, rom in self.onewire_assignments.items() if rom in present}
                temperatures = (self.onewire.read_temperatures(readable.values())
                                if hasattr(self.onewire, "read_temperatures") else
                                {rom: self.onewire.read_temperature(rom) for rom in readable.values()})
                for sensor_id, rom in readable.items():
                    readings.append(SensorReading(
                        sensor_id, "temperature", temperatures[rom], "°C", timestamp=stamp,
                        metadata={"source": "onewire", "adapter": "ds2482",
                                  "device_family": "ds18b20", "rom_id": rom}))
                self.last_successful_onewire_read, self.onewire_last_error = stamp, None
            except Exception as exc:
                self.onewire_last_error = str(exc)
                errors.append(self.onewire_last_error)
        # Preserve the established ADS1115 failure semantics. OneWire is
        # additive/optional, so its failure may degrade only that subsystem.
        if adc_exception is not None:
            raise adc_exception
        if readings:
            return readings
        if errors:
            raise RuntimeError("; ".join(errors))
        return readings

    def health(self):
        assigned = {name: rom for name, rom in self.onewire_assignments.items() if rom}
        present = set(self.discovered_onewire)
        return {
            "mode": "raspberry",
            "i2c_available": self.adc is not None or Path(f"/dev/i2c-{self.bus}").exists(),
            "ads1115_reachable": bool(self.adc and getattr(self.adc, "reachable", True)),
            "acquisition_running": self.last_successful_read is not None,
            "last_successful_read": self.last_successful_read.isoformat() if self.last_successful_read else None,
            "last_error": self.last_error,
            "onewire_enabled": self.onewire_enabled,
            "ds2482_reachable": bool(self.onewire and getattr(self.onewire, "available", False)),
            "onewire_bus_available": bool(self.onewire and getattr(self.onewire, "bus_available", False)),
            "onewire_discovered_count": len(self.discovered_onewire),
            "onewire_assigned_devices": assigned,
            "onewire_unassigned_devices": sorted(present - set(assigned.values())),
            "onewire_missing_devices": {name: rom for name, rom in assigned.items() if rom not in present},
            "last_successful_onewire_read": (self.last_successful_onewire_read.isoformat()
                                              if self.last_successful_onewire_read else None),
            "onewire_last_error": self.onewire_last_error,
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
