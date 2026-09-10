"""Small Linux/SMBus ADS1115 adapter used only by the hardware agent."""
from dataclasses import dataclass
from pathlib import Path
import time

from ..base import ADCReader


class ADS1115Error(RuntimeError):
    """A configuration or I/O failure with useful, non-secret context."""


@dataclass(frozen=True)
class ADCReading:
    raw_count: int
    raw_mv: float


class ADS1115Reader(ADCReader):
    """Single-ended ADS1115 reader with reconnect-on-next-read semantics."""

    GAINS = {
        2 / 3: (0b000, 6.144),
        1: (0b001, 4.096),
        2: (0b010, 2.048),
        4: (0b011, 1.024),
        8: (0b100, 0.512),
        16: (0b101, 0.256),
    }
    DATA_RATES = {8: 0b000, 16: 0b001, 32: 0b010, 64: 0b011,
                  128: 0b100, 250: 0b101, 475: 0b110, 860: 0b111}
    CONVERSION_REGISTER = 0x00
    CONFIG_REGISTER = 0x01

    def __init__(self, bus=1, address=0x48, gain=1, data_rate=128,
                 bus_factory=None, device_exists=None, sleep=time.sleep):
        self.bus_number = int(bus)
        self.address = int(address, 0) if isinstance(address, str) else int(address)
        self.gain = float(gain)
        self.data_rate = int(data_rate)
        if not 0x48 <= self.address <= 0x4B:
            raise ValueError("ADS1115 address must be between 0x48 and 0x4b")
        if self.gain not in self.GAINS:
            raise ValueError(f"unsupported ADS1115 gain: {gain}")
        if self.data_rate not in self.DATA_RATES:
            raise ValueError(f"unsupported ADS1115 data rate: {data_rate}")
        self._factory = bus_factory or self._default_bus_factory
        self._device_exists = device_exists or Path.exists
        self._sleep = sleep
        self._bus = None
        self.reachable = False
        self.last_error = None
        self.initialize()

    @staticmethod
    def _default_bus_factory(number):
        from smbus2 import SMBus
        return SMBus(number)

    def initialize(self):
        device = Path(f"/dev/i2c-{self.bus_number}")
        if not self._device_exists(device):
            self.last_error = f"I2C bus device unavailable: {device}"
            raise ADS1115Error(self.last_error)
        try:
            self._bus = self._factory(self.bus_number)
            self._bus.read_word_data(self.address, self.CONFIG_REGISTER)
            self.reachable, self.last_error = True, None
        except (OSError, IOError) as exc:
            self._disconnect()
            self.last_error = f"ADS1115 at 0x{self.address:02x} did not respond: {exc}"
            raise ADS1115Error(self.last_error) from exc

    def _disconnect(self):
        if self._bus is not None:
            close = getattr(self._bus, "close", None)
            if close:
                close()
        self._bus, self.reachable = None, False

    def read_channel(self, channel):
        if channel not in range(4):
            raise ValueError("ADS1115 channel must be 0, 1, 2, or 3")
        if self._bus is None:
            self.initialize()
        pga, full_scale_volts = self.GAINS[self.gain]
        mux = 0b100 + channel
        config = (1 << 15) | (mux << 12) | (pga << 9) | (1 << 8) | \
                 (self.DATA_RATES[self.data_rate] << 5) | 0b11
        try:
            # SMBus word operations are little-endian; ADS1115 registers are big-endian.
            swapped = ((config & 0xFF) << 8) | (config >> 8)
            self._bus.write_word_data(self.address, self.CONFIG_REGISTER, swapped)
            self._sleep(1 / self.data_rate + 0.001)
            word = self._bus.read_word_data(self.address, self.CONVERSION_REGISTER)
            raw = ((word & 0xFF) << 8) | (word >> 8)
            if raw & 0x8000:
                raw -= 0x10000
            self.reachable, self.last_error = True, None
            return ADCReading(raw, raw * full_scale_volts * 1000 / 32768)
        except (OSError, IOError) as exc:
            self._disconnect()
            self.last_error = f"ADS1115 channel A{channel} read failed: {exc}"
            raise ADS1115Error(self.last_error) from exc
