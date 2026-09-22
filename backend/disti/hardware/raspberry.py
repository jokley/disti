"""Raspberry Pi sensor provider composing independent I2C adapters."""
from datetime import datetime, timezone
import os
from pathlib import Path

from .base import SensorReader, SensorReading

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
        if self.onewire_type not in ("disabled", "ds2484"):
            raise ValueError("unsupported DISTI_ONEWIRE_TYPE (expected ds2484 or disabled)")
        self.onewire_enabled = self.onewire_type == "ds2484"
        self._onewire_factory = onewire_factory
        self.onewire = onewire
        self.onewire_bus = int(os.getenv("DISTI_DS2484_I2C_BUS", str(self.bus)))
        self.onewire_address = os.getenv("DISTI_DS2484_ADDRESS", "0x18")
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
            from .adc.ads1115 import ADS1115Reader
            self._factory = ADS1115Reader
        self.adc = self._factory(bus=self.bus, address=self.address,
                                 gain=float(os.getenv("DISTI_ADS1115_GAIN", "1")),
                                 data_rate=int(os.getenv("DISTI_ADS1115_DATA_RATE", "128")))

    def _initialize_onewire(self):
        if self._onewire_factory is None:
            from .onewire.ds2484 import DS2484OneWireReader
            self._onewire_factory = DS2484OneWireReader
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
                        metadata={"source": "onewire", "adapter": "ds2484",
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
            "ds2484_reachable": bool(self.onewire and getattr(self.onewire, "available", False)),
            "onewire_bus_available": bool(self.onewire and getattr(self.onewire, "bus_available", False)),
            "onewire_discovered_count": len(self.discovered_onewire),
            "onewire_assigned_devices": assigned,
            "onewire_unassigned_devices": sorted(present - set(assigned.values())),
            "onewire_missing_devices": {name: rom for name, rom in assigned.items() if rom not in present},
            "last_successful_onewire_read": (self.last_successful_onewire_read.isoformat()
                                              if self.last_successful_onewire_read else None),
            "onewire_last_error": self.onewire_last_error,
        }

