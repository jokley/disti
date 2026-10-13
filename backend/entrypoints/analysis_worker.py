"""One independent process for continuous, run-free Process Analysis."""
import logging
import os
import signal
from threading import Event

from disti.process_analysis.worker import AnalysisWorker
from disti.repository import Repository


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    stop = Event()
    def shutdown(signum, frame):
        stop.set()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    AnalysisWorker(Repository.from_environment(),
                   poll_seconds=float(os.getenv('DISTI_ANALYSIS_POLL_SECONDS', '2'))).run(stop)


if __name__ == '__main__':
    main()
