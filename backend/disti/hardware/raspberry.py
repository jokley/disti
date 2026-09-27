"""Raspberry Pi sensor provider composing independent I2C adapters."""
from datetime import datetime, timezone
import os
from pathlib import Path

from .base import SensorReader, SensorReading

# Linear calibration measured on QA DISTI hardware against two DS18B20
# references during a slow cooling curve. Input is the ADS1115 reading in mV.
PT1000_TEMPERATURE_SLOPE_C_PER_MV = 0.0601035
PT1000_TEMPERATURE_OFFSET_C = -20.0625

# DFRobot SEN0451 / DFRobot_ECPRO conversion constants.  The K factor was
# calibrated from 1617.6 mV in 1413 uS/cm (at 25 C) solution measured at
# 21.32 C. DFRobot_ECPRO uses 2%/C to normalize conductivity to 25 C.
DFROBOT_ECPRO_RES2_OHMS = 820.0
DFROBOT_ECPRO_ECREF = 2.0
DFROBOT_ECPRO_REFERENCE_TEMPERATURE_C = 25.0
DFROBOT_ECPRO_TEMPERATURE_COEFFICIENT = 0.02
EC_CALIBRATION_VOLTAGE_MV = 1617.6
EC_CALIBRATION_TEMPERATURE_C = 21.32
EC_CALIBRATION_REFERENCE_US_CM_AT_25_C = 1413.0
EC_K_FACTOR = 1.3271298516320476


def pt1000_temperature_c(raw_mv):
    """Convert the calibrated ec-temp PT1000 millivolts to degrees Celsius."""
    return raw_mv * PT1000_TEMPERATURE_SLOPE_C_PER_MV + PT1000_TEMPERATURE_OFFSET_C


def ecpro_k_factor(voltage_mv, reference_us_cm):
    """Return K using DFRobot_ECPRO::calibrate voltage/reference semantics."""
    return (reference_us_cm * DFROBOT_ECPRO_RES2_OHMS * DFROBOT_ECPRO_ECREF /
            (1000.0 * voltage_mv))


def ecpro_us_cm(voltage_mv, temperature_c=None, k_factor=EC_K_FACTOR):
    """Port DFRobot_ECPRO::getEC_us_cm, optionally compensated to 25 C."""
    conductivity = (1000.0 * voltage_mv * k_factor /
                    DFROBOT_ECPRO_RES2_OHMS / DFROBOT_ECPRO_ECREF)
    if temperature_c is None:
        return conductivity
    temperature_factor = 1.0 + DFROBOT_ECPRO_TEMPERATURE_COEFFICIENT * (
        temperature_c - DFROBOT_ECPRO_REFERENCE_TEMPERATURE_C)
    return conductivity / temperature_factor


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
            samples = {
                sensor_id: self.adc.read_channel(channel)
                for sensor_id, _, channel in self.channels
            }
            ec_temperature_c = pt1000_temperature_c(samples["ec-temp"].raw_mv)
            for sensor_id, measurement_type, channel in self.channels:
                sample = samples[sensor_id]
                is_pt1000 = sensor_id == "ec-temp"
                is_ec = sensor_id == "ec-1"
                readings.append(SensorReading(
                    sensor_id, measurement_type,
                    (ec_temperature_c if is_pt1000 else
                     ecpro_us_cm(sample.raw_mv, ec_temperature_c)),
                    "°C" if is_pt1000 else "µS/cm", timestamp=stamp,
                    raw_value=sample.raw_count, raw_mv=sample.raw_mv,
                    metadata={"adc_type": "ads1115", "channel": channel,
                              "engineering_conversion": ("pt1000_qa_linear_calibration"
                                                         if is_pt1000 else
                                                         "dfrobot_ecpro_sen0451"),
                              **({"temperature_c": ec_temperature_c,
                                  "k_factor": EC_K_FACTOR} if is_ec else {})}))
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
