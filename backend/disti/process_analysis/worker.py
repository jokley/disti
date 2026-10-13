"""Single live consumer; no detector logic or persistent analyzer checkpoint."""
import logging
from datetime import datetime, timedelta, timezone
from threading import Event

from .service import AnalysisService, bucket_points, floor_bucket, timestamp

logger = logging.getLogger(__name__)


class AnalysisWorker:
    def __init__(self, repository, service=None, poll_seconds=2, clock=None):
        if poll_seconds <= 0:
            raise ValueError('poll_seconds must be positive')
        self.repository = repository
        self.service = service or AnalysisService(repository)
        self.poll_seconds = poll_seconds
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.analyzer = None
        self.next_bucket = None

    def _initialize(self, cutoff):
        c = self.service.config
        latest = self.repository.latest_analysis_time(self.service.analyzer_type.detector_name, c.algo_version)
        analyzer = self.service.analyzer_type(c)
        if latest is not None:
            # Restore all state, including frozen baseline/CUSUM, without
            # rewriting stored results. Only the missing tail is persisted.
            resume = min(timestamp(latest) + timedelta(seconds=c.bucket_seconds), cutoff)
            rows = self.repository.analysis_buckets(resume, c.bucket_seconds, c.valid_sensor_qualities)
            for point in bucket_points(rows, resume, c):
                analyzer.update(point)
        else:
            first = self.repository.first_analysis_measurement_time()
            if first is None:
                return
            resume = floor_bucket(timestamp(first), c.bucket_seconds)
        self.analyzer, self.next_bucket = analyzer, resume
        logger.info('Analysis ready; next bucket %s', resume.isoformat())

    def tick(self):
        """Process every newly completed bucket once in this running analyzer."""
        c = self.service.config
        cutoff = floor_bucket(timestamp(self.clock()), c.bucket_seconds)
        written = 0
        try:
            if self.analyzer is None:
                self._initialize(cutoff)
            while self.next_bucket is not None and self.next_bucket < cutoff:
                self.service.process_completed_bucket(self.analyzer, self.next_bucket)
                # Advance only after successful persistence. A failed save may
                # already have mutated the analyzer; restore from DB on retry.
                self.next_bucket += timedelta(seconds=c.bucket_seconds)
                written += 1
        except Exception:
            self.analyzer = None
            self.next_bucket = None
            raise
        return written

    def run(self, stop=None):
        stop = stop or Event()
        while not stop.is_set():
            try:
                written = self.tick()
                if written:
                    logger.info('Stored %s completed analysis buckets', written)
            except Exception:
                logger.exception('Live analysis failed; retrying after %.1f seconds', self.poll_seconds)
            stop.wait(self.poll_seconds)
