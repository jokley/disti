import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

sys.modules.setdefault("docker", SimpleNamespace(from_env=lambda: None))
sys.modules.setdefault("requests", SimpleNamespace())
sys.modules.setdefault("psycopg2", SimpleNamespace())
spec = importlib.util.spec_from_file_location("disti_watchdog", Path(__file__).parents[1] / "watchdog.py")
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class Container:
    attrs = {"State": {"Status": "running"}}
    def __init__(self): self.restarts = 0
    def reload(self): pass
    def logs(self, tail): return b"diagnostic"
    def restart(self): self.restarts += 1


class Client:
    def __init__(self): self.items = {}
    @property
    def containers(self): return self
    def get(self, name): return self.items.setdefault(name, Container())


class HTTP:
    def __init__(self, health): self.health = iter(health)
    def get(self, url, timeout): return SimpleNamespace(ok=next(self.health))


def test_backend_is_rechecked_and_restart_budget_is_enforced(monkeypatch):
    client = Client(); clock = [1000]
    watchdog = module.Watchdog(client=client, http=HTTP([False, False]), clock=lambda: clock[0], sleep=lambda _: None)
    watchdog.check()
    assert client.get("flask-backend").restarts == 1
    assert watchdog.can_restart("flask-backend") is False
    watchdog.restarts.extend([900, 901, 902])
    assert watchdog.can_restart("another") is False
