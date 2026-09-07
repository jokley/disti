"""Independent, restart-safe DISTI acquisition process."""
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from disti.hardware import HardwareManager, MockSensorReader, ReplaySensorReader, RaspberrySensorReader
from disti.repository import Repository


class Agent:
    def __init__(self, repository=None, reader=None, interval=None):
        self.repository = repository or Repository.from_environment()
        self.interval = float(interval or os.getenv("DISTI_POLL_INTERVAL_SECONDS", "2"))
        self.reader = reader or self._reader_from_environment()
        self.manager = HardwareManager([self.reader])
        self.status = {"status": "starting", "last_read_at": None, "last_error": None}

    def _reader_from_environment(self):
        mode = os.getenv("DISTI_HARDWARE_MODE", "mock")
        if mode == "mock": return MockSensorReader()
        if mode == "replay":
            run_id = os.environ["DISTI_REPLAY_RUN_ID"]
            preserve = os.getenv("DISTI_REPLAY_PRESERVE_TIMING", "true").lower() == "true"
            return ReplaySensorReader(self.repository, run_id, os.getenv("DISTI_REPLAY_SPEED", "1"), preserve)
        if mode == "raspberry": return RaspberrySensorReader()
        raise ValueError(f"unsupported DISTI_HARDWARE_MODE: {mode}")

    def poll_once(self):
        run = self.repository.active_run()
        for reading in self.manager.read_all():
            self.repository.ensure_sensor(reading.sensor_id, reading.sensor_id, reading.measurement_type)
            self.repository.save_measurement(reading, run["id"] if run else None)
        self.status.update(status="healthy", last_read_at=time.time(), last_error=None)

    def run(self):
        delay = self.interval
        while True:
            try:
                self.poll_once(); delay = self.interval
            except StopIteration:
                self.status["status"] = "replay-complete"; return
            except Exception as exc:  # process must survive transient bus/database failures
                self.status.update(status="degraded", last_error=str(exc))
                delay = min(max(delay * 2, 1), 30)
            time.sleep(delay)


def serve_health(agent):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps(agent.status).encode()
            self.send_response(200 if agent.status["status"] in ("healthy", "replay-complete") else 503)
            self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
        def log_message(self, *_): pass
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("DISTI_HARDWARE_HEALTH_PORT", "8081"))), Handler).serve_forever()


if __name__ == "__main__":
    agent = Agent()
    Thread(target=serve_health, args=(agent,), daemon=True).start()
    agent.run()
