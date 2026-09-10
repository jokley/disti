"""Hardware orchestration and fraction-collector abstractions."""

from .base import FractionCollector

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
