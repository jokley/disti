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
    def __init__(self, state=None):
        self.attrs = {"State": state or {"Status": "running", "Running": True}}
        self.restarts = 0
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


class StatusHTTP:
    def get(self, url, timeout):
        if url.endswith("healthz"):
            return SimpleNamespace(ok=True)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"database": {"healthy": True}, "hardware_agent": {"healthy": False}},
        )


def test_backend_is_rechecked_and_restart_budget_is_enforced(monkeypatch):
    client = Client(); clock = [1000]
    watchdog = module.Watchdog(client=client, http=HTTP([False, False]), clock=lambda: clock[0], sleep=lambda _: None)
    watchdog.check()
    assert client.get("disti-api").restarts == 1
    assert watchdog.can_restart("disti-api") is False
    watchdog.restarts.extend([900, 901, 902])
    assert watchdog.can_restart("another") is False


def test_hardware_starting_is_not_restarted_when_api_is_unhealthy():
    client = Client()
    client.items["disti-hardware-agent"] = Container({
        "Status": "running", "Running": True,
        "Health": {"Status": "starting", "FailingStreak": 0},
        "StartedAt": "2026-09-25T11:59:00Z",
    })
    watchdog = module.Watchdog(
        client=client, http=StatusHTTP(), clock=lambda: 1000,
        wall_clock=lambda: 1790337600, sleep=lambda _: None,
    )

    watchdog.check()

    assert client.get("disti-hardware-agent").restarts == 0


def test_docker_healthy_container_is_not_restarted_for_stale_api_status():
    client = Client()
    client.items["disti-hardware-agent"] = Container({
        "Status": "running", "Running": True,
        "Health": {"Status": "healthy", "FailingStreak": 0},
        "StartedAt": "2026-09-25T11:00:00Z",
    })
    watchdog = module.Watchdog(client=client, http=StatusHTTP(), wall_clock=lambda: 1790337600)

    watchdog.check()

    assert client.get("disti-hardware-agent").restarts == 0


def test_unhealthy_container_is_restarted_after_startup_grace():
    client = Client()
    container = Container({
        "Status": "running", "Running": True,
        "Health": {"Status": "unhealthy", "FailingStreak": 3},
        "StartedAt": "2026-09-25T11:00:00Z",
    })
    client.items["disti-hardware-agent"] = container
    watchdog = module.Watchdog(client=client, http=StatusHTTP(), wall_clock=lambda: 1790337600)

    watchdog.check()

    assert container.restarts == 1


def test_recently_started_unhealthy_container_waits_for_grace(monkeypatch):
    monkeypatch.setenv("WATCHDOG_STARTUP_GRACE_SEC", "60")
    client = Client()
    container = Container({
        "Status": "running", "Running": True,
        "Health": {"Status": "unhealthy", "FailingStreak": 3},
        "StartedAt": "2026-09-25T11:59:30Z",
    })
    client.items["disti-hardware-agent"] = container
    watchdog = module.Watchdog(client=client, http=StatusHTTP(), wall_clock=lambda: 1790337600)

    watchdog.check()

    assert container.restarts == 0


def test_stopped_and_dead_containers_are_restarted_after_grace():
    for docker_status in ("exited", "dead"):
        client = Client()
        container = Container({
            "Status": docker_status, "Running": False,
            "StartedAt": "2026-09-25T11:00:00Z",
        })
        client.items["disti-postgres"] = container
        watchdog = module.Watchdog(client=client, wall_clock=lambda: 1790337600)

        assert watchdog.restart("disti-postgres") is True
        assert container.restarts == 1
