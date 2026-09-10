"""Hardware abstraction layer; business logic depends only on these protocols."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


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


