import pytest

from disti.hardware.onewire.ds2482 import DS2482OneWireReader, OneWireError, crc8
from disti.hardware import RaspberrySensorReader
from entrypoints.hardware_agent import Agent


def rom(serial):
    raw = bytes([0x28]) + int(serial).to_bytes(6, "little")
    raw += bytes([crc8(raw)])
    return DS2482OneWireReader.format_rom(raw)


class FakeSMBus:
    def __init__(self, fail_reset=False):
        self.fail_reset = fail_reset
        self.writes = []
        self.closed = False

    def write_byte(self, address, value):
        self.writes.append(("byte", address, value))
        if self.fail_reset:
            raise OSError("remote I/O")

    def write_byte_data(self, address, command, value):
        self.writes.append(("data", address, command, value))

    def read_byte(self, address):
        return 0x10

    def close(self):
        self.closed = True


def test_initialization_uses_configured_bus_address_and_configures_apu():
    bus, opened = FakeSMBus(), []
    reader = DS2482OneWireReader(bus=3, address="0x1a",
        bus_factory=lambda number: opened.append(number) or bus,
        device_exists=lambda _: True, sleep=lambda _: None)
    assert opened == [3]
    assert bus.writes == [("byte", 0x1a, 0xF0), ("data", 0x1a, 0xD2, 0xE1)]
    assert reader.available and reader.bus_available


def test_missing_i2c_bus_and_nonresponding_ds2482_are_meaningful():
    with pytest.raises(OneWireError, match="/dev/i2c-7"):
        DS2482OneWireReader(bus=7, device_exists=lambda _: False)
    with pytest.raises(OneWireError, match="0x18 did not respond"):
        DS2482OneWireReader(bus_factory=lambda _: FakeSMBus(True),
                            device_exists=lambda _: True)


class SearchReader(DS2482OneWireReader):
    """Protocol harness emulating DS2482 triplets over a set of ROM bit streams."""
    def __init__(self, devices):
        self.devices = [self.parse_rom(item) for item in devices]
        self.reachable = True
        self.bus_available = True
        self.last_error = None
        self._bus = object()
        self.active = []
        self.bit = 0

    def _ensure(self): pass

    def _reset_bus(self):
        self.active, self.bit = list(self.devices), 0
        return bool(self.active)

    def _write_byte(self, value):
        assert value == 0xF0

    def _triplet(self, direction):
        values = [(item[self.bit // 8] >> (self.bit % 8)) & 1 for item in self.active]
        have_zero, have_one = 0 in values, 1 in values
        if have_zero and have_one:
            chosen, status = int(direction), 0x80 if direction else 0
        elif have_one:
            chosen, status = 1, 0xA0
        else:
            chosen, status = 0, 0x40
        self.active = [item for item in self.active
                       if ((item[self.bit // 8] >> (self.bit % 8)) & 1) == chosen]
        self.bit += 1
        return status


def test_presence_no_presence_and_rom_search_one_or_multiple_devices():
    first, second = rom(1), rom(2)
    assert SearchReader([]).discover() == []
    assert SearchReader([first]).discover() == [first]
    assert set(SearchReader([first, second]).discover()) == {first, second}


class TemperatureReader(DS2482OneWireReader):
    def __init__(self, scratchpads):
        self.scratchpads = scratchpads
        self.selected = None
        self.reachable = True
        self.bus_available = True
        self.last_error = None
        self._bus = object()
        self._sleep = lambda value: setattr(self, "slept", value)
        self.conversion_time = 0.75

    def _ensure(self): pass
    def _reset_bus(self): return True
    def _write_byte(self, value): pass
    def _select(self, raw): self.selected = self.format_rom(raw)
    def _read_byte(self): return next(self.current)
    def _scratchpad(self, raw):
        self.current = iter(self.scratchpads[self.format_rom(raw)])
        return super()._scratchpad(raw)


def scratchpad(raw):
    data = int(raw).to_bytes(2, "little", signed=True) + bytes([0x4B, 0x46, 0x7F, 0xFF, 0x0C, 0x10])
    return data + bytes([crc8(data)])


@pytest.mark.parametrize(("raw", "expected"), [(0x04EA, 78.625), (-162, -10.125)])
def test_positive_and_negative_temperature_and_conversion_wait(raw, expected):
    sensor = rom(9)
    reader = TemperatureReader({sensor: scratchpad(raw)})
    assert reader.read_temperature(sensor) == expected
    assert reader.slept == 0.75


def test_scratchpad_crc_failure_is_rejected():
    sensor = rom(10)
    bad = bytearray(scratchpad(400)); bad[-1] ^= 1
    with pytest.raises(OneWireError, match="scratchpad CRC"):
        TemperatureReader({sensor: bad}).read_temperature(sensor)


def test_transient_i2c_failure_disconnects_and_reinitializes():
    failed, recovered = FakeSMBus(), FakeSMBus()
    buses = iter([failed, recovered])
    reader = DS2482OneWireReader(bus_factory=lambda _: next(buses),
                                 device_exists=lambda _: True, sleep=lambda _: None)
    failed.write_byte = lambda *_: (_ for _ in ()).throw(OSError("temporary"))
    with pytest.raises(OneWireError, match="discovery failed"):
        reader.discover()
    assert failed.closed and not reader.available
    # The next operation opens a fresh SMBus and sees no 1-Wire presence.
    assert reader.discover() == []
    assert reader.available


class FakeADC:
    reachable = True
    def read_channel(self, channel):
        return type("Sample", (), {"raw_count": channel, "raw_mv": float(channel)})()


class FakeOneWire:
    available = True
    bus_available = True
    def __init__(self, devices, values=None):
        self.devices, self.values = devices, values or {}
    def discover(self): return self.devices
    def read_temperatures(self, ids): return {item: self.values[item] for item in ids}


def test_assigned_unassigned_and_missing_mapping_is_stable(monkeypatch):
    vapor, unknown, missing = rom(11), rom(12), rom(13)
    monkeypatch.setenv("DISTI_ONEWIRE_TYPE", "ds2482")
    monkeypatch.setenv("DISTI_ONEWIRE_VAPOR_ID", vapor)
    monkeypatch.setenv("DISTI_ONEWIRE_RESERVE_ID", missing)
    reader = RaspberrySensorReader(adc=FakeADC(), onewire=FakeOneWire([vapor, unknown], {vapor: 78.625}))
    readings = reader.read()
    temp = next(item for item in readings if item.sensor_id == "vapor-temp")
    assert temp.value == 78.625 and temp.unit == "°C" and temp.metadata["rom_id"] == vapor
    health = reader.health()
    assert health["onewire_unassigned_devices"] == [unknown]
    assert health["onewire_missing_devices"] == {"reserve-temp": missing}
    assert all(item.sensor_id != "reserve-temp" for item in readings)


def test_raspberry_selects_ds2482_configuration(monkeypatch):
    monkeypatch.setenv("DISTI_ONEWIRE_TYPE", "ds2482")
    monkeypatch.setenv("DISTI_DS2482_I2C_BUS", "4")
    monkeypatch.setenv("DISTI_DS2482_ADDRESS", "0x1b")
    captured = {}
    RaspberrySensorReader(adc=FakeADC(), onewire_factory=lambda **kw: captured.update(kw) or FakeOneWire([]))
    assert captured == {"bus": 4, "address": "0x1b"}


def test_missing_bridge_does_not_crash_constructor_or_adc_acquisition(monkeypatch):
    monkeypatch.setenv("DISTI_ONEWIRE_TYPE", "ds2482")
    reader = RaspberrySensorReader(adc=FakeADC(),
        onewire_factory=lambda **_: (_ for _ in ()).throw(OneWireError("bridge unavailable")))
    assert len(reader.read()) == 2
    assert reader.health()["onewire_last_error"] == "bridge unavailable"


def test_mock_replay_provider_selection_remains_hardware_free(monkeypatch, repo):
    monkeypatch.setenv("DISTI_ONEWIRE_TYPE", "ds2482")
    monkeypatch.setenv("DISTI_HARDWARE_MODE", "mock")
    assert Agent(repo).reader.__class__.__name__ == "MockSensorReader"
    monkeypatch.setenv("DISTI_HARDWARE_MODE", "replay")
    monkeypatch.setenv("DISTI_REPLAY_RUN_ID", "run")
    repo.replay_measurements = lambda _: []
    assert Agent(repo).reader.__class__.__name__ == "ReplaySensorReader"
