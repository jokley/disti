import pytest

from disti.hardware.adc.ads1115 import ADS1115Error, ADS1115Reader
from disti.hardware import RaspberrySensorReader
from entrypoints.hardware_agent import Agent


def ads_word(raw):
    raw &= 0xFFFF
    return ((raw & 0xFF) << 8) | (raw >> 8)


class FakeBus:
    def __init__(self, conversions=(), probe_error=None):
        self.conversions = iter(conversions)
        self.probe_error = probe_error
        self.reads = []
        self.writes = []
        self.closed = False

    def read_word_data(self, address, register):
        self.reads.append((address, register))
        if register == 1:
            if self.probe_error:
                raise self.probe_error
            return 0
        value = next(self.conversions)
        if isinstance(value, Exception):
            raise value
        return ads_word(value)

    def write_word_data(self, address, register, value):
        self.writes.append((address, register, value))

    def close(self):
        self.closed = True


def make_reader(bus, **kwargs):
    return ADS1115Reader(bus_factory=lambda number: bus, device_exists=lambda _: True,
                         sleep=lambda _: None, **kwargs)


def test_initialization_uses_configured_bus_and_address():
    bus = FakeBus()
    buses = []
    reader = ADS1115Reader(bus=3, address="0x49",
                           bus_factory=lambda number: buses.append(number) or bus,
                           device_exists=lambda _: True, sleep=lambda _: None)
    assert buses == [3]
    assert bus.reads == [(0x49, 1)]
    assert reader.reachable


@pytest.mark.parametrize(("channel", "raw"), [(0, 16384), (1, -8192)])
def test_a0_a1_preserve_raw_count_and_convert_millivolts(channel, raw):
    bus = FakeBus([raw])
    sample = make_reader(bus, gain=1).read_channel(channel)
    assert sample.raw_count == raw
    assert sample.raw_mv == pytest.approx(raw * 4096 / 32768)
    config = ((bus.writes[0][2] & 0xFF) << 8) | (bus.writes[0][2] >> 8)
    assert (config >> 12) & 0b111 == 0b100 + channel


def test_invalid_channel_is_rejected():
    with pytest.raises(ValueError, match="channel"):
        make_reader(FakeBus()).read_channel(4)


def test_unavailable_bus_is_reported():
    with pytest.raises(ADS1115Error, match="/dev/i2c-7"):
        ADS1115Reader(bus=7, device_exists=lambda _: False)


def test_nonresponding_adc_is_reported():
    with pytest.raises(ADS1115Error, match="0x48 did not respond"):
        make_reader(FakeBus(probe_error=OSError("remote I/O")))


def test_transient_read_failure_disconnects_and_next_read_recovers():
    failed, recovered = FakeBus([OSError("temporary")]), FakeBus([100])
    buses = iter([failed, recovered])
    reader = ADS1115Reader(bus_factory=lambda _: next(buses), device_exists=lambda _: True,
                           sleep=lambda _: None)
    with pytest.raises(ADS1115Error, match="A0 read failed"):
        reader.read_channel(0)
    assert not reader.reachable and failed.closed
    assert reader.read_channel(0).raw_count == 100
    assert reader.reachable and reader.last_error is None


class FakeADC:
    reachable = True
    def __init__(self): self.channels = []
    def read_channel(self, channel):
        self.channels.append(channel)
        return type("Sample", (), {"raw_count": 100 + channel, "raw_mv": 12.5 + channel})()


def test_raspberry_provider_maps_ec_and_pt1000_without_calibration():
    adc = FakeADC()
    reader = RaspberrySensorReader(adc=adc)
    readings = reader.read()
    assert adc.channels == [0, 1]
    assert [(r.sensor_id, r.measurement_type) for r in readings] == [
        ("ec-1", "ec"), ("ec-temp", "temperature")]
    assert readings[0].raw_value == 100 and readings[0].raw_mv == 12.5
    assert readings[1].raw_value == 101 and readings[1].raw_mv == 13.5
    assert readings[0].unit == "mV"
    assert readings[0].calibration_id is None
    assert readings[0].metadata["engineering_conversion"] == "not_configured"
    assert reader.health()["acquisition_running"]


def test_raspberry_provider_selects_ads1115_configuration(monkeypatch):
    monkeypatch.setenv("DISTI_I2C_BUS", "2")
    monkeypatch.setenv("DISTI_ADS1115_ADDRESS", "0x4a")
    captured = {}
    def factory(**kwargs):
        captured.update(kwargs)
        return FakeADC()
    RaspberrySensorReader(adc_factory=factory)
    assert captured == {"bus": 2, "address": "0x4a", "gain": 1.0, "data_rate": 128}


def test_raspberry_initialization_failure_is_degraded_not_constructor_crash():
    reader = RaspberrySensorReader(adc_factory=lambda **_: (_ for _ in ()).throw(ADS1115Error("missing")))
    assert reader.adc is None
    assert reader.health()["last_error"] == "missing"
    assert not reader.health()["ads1115_reachable"]


def test_agent_factory_keeps_mock_and_replay_modes(monkeypatch, repo):
    monkeypatch.setenv("DISTI_HARDWARE_MODE", "mock")
    assert Agent(repo).reader.__class__.__name__ == "MockSensorReader"
    monkeypatch.setenv("DISTI_HARDWARE_MODE", "replay")
    monkeypatch.setenv("DISTI_REPLAY_RUN_ID", "run")
    repo.replay_measurements = lambda _: []
    assert Agent(repo).reader.__class__.__name__ == "ReplaySensorReader"
