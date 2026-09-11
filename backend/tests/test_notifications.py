import logging
import threading
import time
import urllib.error

import pytest

from disti.notifications import ntfy


class Response:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status


@pytest.fixture(autouse=True)
def ntfy_environment(monkeypatch):
    monkeypatch.setenv("DISTI_NTFY_ENABLED", "true")
    monkeypatch.setenv("DISTI_NTFY_BASE_URL", "https://notify.example/root/")
    monkeypatch.setenv("DISTI_NTFY_TOPIC", "test topic")


def run_inline(monkeypatch):
    class InlineThread:
        def __init__(self, target, args, **kwargs):
            self.target, self.args, self.kwargs = target, args, kwargs

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(ntfy.threading, "Thread", InlineThread)


def test_disabled_does_not_start_worker(monkeypatch):
    monkeypatch.setenv("DISTI_NTFY_ENABLED", "false")
    monkeypatch.setattr(ntfy.threading, "Thread", lambda **kwargs: pytest.fail("worker started"))
    assert ntfy.send_notification("title", "message") is None


def test_success_uses_configured_endpoint_and_formats_utf8(monkeypatch):
    run_inline(monkeypatch)
    captured = {}

    def urlopen(request, timeout):
        captured.update(url=request.full_url, body=request.data, timeout=timeout,
                        content_type=request.get_header("Content-type"))
        return Response()

    monkeypatch.setattr(ntfy.urllib.request, "urlopen", urlopen)
    ntfy.send_notification("Still title", "Temperatur: 78 °C")

    assert captured == {
        "url": "https://notify.example/root/test%20topic",
        "body": "Still title\n\nTemperatur: 78 °C".encode(),
        "timeout": ntfy.HTTP_TIMEOUT_SECONDS,
        "content_type": "text/plain; charset=utf-8",
    }


def test_empty_topic_logs_sanitized_warning(monkeypatch, caplog):
    monkeypatch.setenv("DISTI_NTFY_TOPIC", "  ")
    with caplog.at_level(logging.WARNING):
        ntfy.send_notification("secret title", "secret message")
    assert "DISTI_NTFY_TOPIC is empty" in caplog.text
    assert "secret" not in caplog.text


@pytest.mark.parametrize("failure", [
    urllib.error.URLError("offline"),
    TimeoutError("slow"),
])
def test_connection_failures_are_logged_not_raised(monkeypatch, caplog, failure):
    run_inline(monkeypatch)
    monkeypatch.setattr(ntfy.urllib.request, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(failure))
    with caplog.at_level(logging.WARNING):
        assert ntfy.send_notification("title", "message") is None
    assert "delivery failed" in caplog.text


def test_non_200_response_is_logged(monkeypatch, caplog):
    run_inline(monkeypatch)
    monkeypatch.setattr(ntfy.urllib.request, "urlopen", lambda *args, **kwargs: Response(503))
    with caplog.at_level(logging.WARNING):
        ntfy.send_notification("title", "message")
    assert "HTTP status 503" in caplog.text


def test_worker_start_failure_does_not_propagate(monkeypatch, caplog):
    class BrokenThread:
        def __init__(self, **kwargs):
            pass

        def start(self):
            raise RuntimeError("no threads")

    monkeypatch.setattr(ntfy.threading, "Thread", BrokenThread)
    with caplog.at_level(logging.ERROR):
        assert ntfy.send_notification("title", "message") is None
    assert "Unable to start" in caplog.text


def test_send_is_fire_and_forget(monkeypatch):
    entered = threading.Event()
    release = threading.Event()

    def slow_urlopen(*args, **kwargs):
        entered.set()
        release.wait(2)
        return Response()

    monkeypatch.setattr(ntfy.urllib.request, "urlopen", slow_urlopen)
    started = time.monotonic()
    ntfy.send_notification("title", "message")
    elapsed = time.monotonic() - started
    try:
        assert entered.wait(1)
        assert elapsed < 0.25
    finally:
        release.set()
