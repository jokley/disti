"""DS2482-100 I2C-to-1-Wire adapter and DS18B20 protocol handling."""
from pathlib import Path
import re
import time

from ..base import OneWireReader


class OneWireError(RuntimeError):
    """Sanitized adapter, bus, or sensor failure."""


def crc8(data):
    crc = 0
    for value in data:
        byte = value
        for _ in range(8):
            mix = (crc ^ byte) & 1
            crc >>= 1
            if mix:
                crc ^= 0x8C
            byte >>= 1
    return crc


class DS2482OneWireReader(OneWireReader):
    DEVICE_RESET = 0xF0
    SET_READ_POINTER = 0xE1
    WRITE_CONFIG = 0xD2
    ONEWIRE_RESET = 0xB4
    ONEWIRE_WRITE_BYTE = 0xA5
    ONEWIRE_READ_BYTE = 0x96
    ONEWIRE_TRIPLET = 0x78
    STATUS_POINTER = 0xF0
    STATUS_BUSY = 0x01
    STATUS_PRESENCE = 0x02
    STATUS_SHORT = 0x04
    STATUS_RESET = 0x10

    def __init__(self, bus=1, address=0x18, bus_factory=None, device_exists=None,
                 sleep=time.sleep, conversion_time=0.75):
        self.bus_number = int(bus)
        self.address = int(address, 0) if isinstance(address, str) else int(address)
        if not 0x18 <= self.address <= 0x1f:
            raise ValueError("DS2482 address must be between 0x18 and 0x1f")
        self._factory = bus_factory or self._default_bus_factory
        self._device_exists = device_exists or Path.exists
        self._sleep = sleep
        self.conversion_time = float(conversion_time)
        self._bus = None
        self.reachable = False
        self.bus_available = False
        self.last_error = None
        self.initialize()

    @property
    def available(self):
        return self.reachable

    @staticmethod
    def _default_bus_factory(number):
        from smbus2 import SMBus
        return SMBus(number)

    def initialize(self):
        device = Path(f"/dev/i2c-{self.bus_number}")
        self.bus_available = bool(self._device_exists(device))
        if not self.bus_available:
            raise OneWireError(f"I2C bus device unavailable: {device}")
        try:
            self._bus = self._factory(self.bus_number)
            self._bus.write_byte(self.address, self.DEVICE_RESET)
            status = self._bus.read_byte(self.address)
            if not status & self.STATUS_RESET:
                raise OSError("reset status not reported")
            # Active pull-up enabled; encoded complement protects configuration writes.
            config = 0x01
            self._bus.write_byte_data(self.address, self.WRITE_CONFIG,
                                      config | ((~config & 0x0f) << 4))
            self.reachable, self.last_error = True, None
        except (OSError, IOError) as exc:
            self._fail(f"DS2482 at 0x{self.address:02x} did not respond", exc)

    def _disconnect(self):
        if self._bus is not None:
            close = getattr(self._bus, "close", None)
            if close:
                close()
        self._bus, self.reachable = None, False

    def _fail(self, context, exc):
        self._disconnect()
        self.last_error = f"{context}: {exc}"
        raise OneWireError(self.last_error) from exc

    def _ensure(self):
        if self._bus is None:
            self.initialize()

    def _wait(self):
        for _ in range(100):
            status = self._bus.read_byte(self.address)
            if not status & self.STATUS_BUSY:
                return status
            self._sleep(0.001)
        raise OSError("1-Wire operation timed out")

    def _reset_bus(self):
        self._bus.write_byte(self.address, self.ONEWIRE_RESET)
        status = self._wait()
        if status & self.STATUS_SHORT:
            raise OSError("1-Wire bus short detected")
        return bool(status & self.STATUS_PRESENCE)

    def _write_byte(self, value):
        self._bus.write_byte_data(self.address, self.ONEWIRE_WRITE_BYTE, value)
        self._wait()

    def _read_byte(self):
        self._bus.write_byte(self.address, self.ONEWIRE_READ_BYTE)
        self._wait()
        self._bus.write_byte_data(self.address, self.SET_READ_POINTER, 0xE1)
        return self._bus.read_byte(self.address)

    def _triplet(self, direction):
        self._bus.write_byte_data(self.address, self.ONEWIRE_TRIPLET, 0x80 if direction else 0)
        return self._wait()

    def discover(self):
        try:
            self._ensure()
            found, last_discrepancy, previous = [], 0, [0] * 8
            while True:
                if not self._reset_bus():
                    break
                self._write_byte(0xF0)
                rom, discrepancy = [0] * 8, 0
                for bit_number in range(1, 65):
                    byte_index, mask = (bit_number - 1) // 8, 1 << ((bit_number - 1) % 8)
                    if bit_number < last_discrepancy:
                        direction = bool(previous[byte_index] & mask)
                    else:
                        direction = bit_number == last_discrepancy
                    status = self._triplet(direction)
                    chosen = bool(status & 0x80)
                    # A discrepancy exists only when SBR and TSB are both zero.
                    if (status & 0x60) == 0 and not chosen:
                        discrepancy = bit_number
                    if chosen:
                        rom[byte_index] |= mask
                if crc8(rom[:7]) != rom[7]:
                    raise OneWireError("discovered 1-Wire ROM failed CRC validation")
                previous, last_discrepancy = rom, discrepancy
                if rom[0] == 0x28:
                    found.append(self.format_rom(rom))
                if last_discrepancy == 0:
                    break
            self.reachable, self.last_error = True, None
            return found
        except OneWireError:
            raise
        except (OSError, IOError) as exc:
            self._fail("DS2482 1-Wire discovery failed", exc)

    @staticmethod
    def format_rom(rom):
        # Use the familiar family-serial form externally; the wire CRC byte is
        # validated on discovery and reconstructed when an ID is configured.
        return f"{rom[0]:02x}-" + "".join(f"{b:02x}" for b in rom[1:7])

    @staticmethod
    def parse_rom(rom_id):
        if not re.fullmatch(r"[0-9a-fA-F]{2}-[0-9a-fA-F]{12}", rom_id):
            raise ValueError("1-Wire ROM ID must use 28-xxxxxxxxxxxx format")
        identity = bytes.fromhex(rom_id.replace("-", ""))
        if identity[0] != 0x28:
            raise ValueError("1-Wire ROM ID is not a DS18B20 family ID")
        return identity + bytes([crc8(identity)])

    def _select(self, raw):
        if not self._reset_bus():
            raise OneWireError("no 1-Wire devices present")
        self._write_byte(0x55)
        for byte in raw:
            self._write_byte(byte)

    def _scratchpad(self, raw):
        self._select(raw)
        self._write_byte(0xBE)
        data = bytes(self._read_byte() for _ in range(9))
        if crc8(data[:8]) != data[8]:
            raise OneWireError(f"DS18B20 {self.format_rom(raw)} scratchpad CRC failure")
        signed = int.from_bytes(data[:2], "little", signed=True)
        return signed / 16.0

    def read_temperatures(self, rom_ids):
        raws = {rom.lower(): self.parse_rom(rom) for rom in rom_ids}
        if not raws:
            return {}
        try:
            self._ensure()
            if not self._reset_bus():
                raise OneWireError("no 1-Wire devices present")
            self._write_byte(0xCC)  # Skip ROM: one conversion for every sensor on the bus.
            self._write_byte(0x44)
            self._sleep(self.conversion_time)  # worst case for the default 12-bit resolution
            result = {rom: self._scratchpad(raw) for rom, raw in raws.items()}
            self.reachable, self.last_error = True, None
            return result
        except OneWireError:
            raise
        except (OSError, IOError) as exc:
            self._fail("DS18B20 temperature read failed", exc)

    def read_temperature(self, rom_id):
        normalized = rom_id.lower()
        return self.read_temperatures([normalized])[normalized]
