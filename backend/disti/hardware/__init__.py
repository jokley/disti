"""Hardware contracts, providers, adapters, and orchestration."""

from .base import (
    ADCReader,
    ECProvider,
    FractionCollector,
    OneWireReader,
    SensorReader,
    SensorReading,
    TemperatureProvider,
)
from .manager import HardwareManager, MockFractionCollector
from .providers import MockSensorReader, ReplaySensorReader
from .raspberry import RaspberrySensorReader

__all__ = [
    "ADCReader", "ECProvider", "FractionCollector", "HardwareManager",
    "MockFractionCollector", "MockSensorReader", "OneWireReader",
    "RaspberrySensorReader", "ReplaySensorReader", "SensorReader",
    "SensorReading", "TemperatureProvider",
]
