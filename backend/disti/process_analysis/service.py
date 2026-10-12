"""Orchestration only: replay and live share ProcessAnalyzer.update()."""
from datetime import datetime, timedelta, timezone
from . import AnalysisConfig, AnalysisInput, ProcessAnalyzer


def timestamp(value):
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamps must include a timezone')
    return parsed.astimezone(timezone.utc)


def floor_bucket(time, seconds):
    return datetime.fromtimestamp(int(time.timestamp()) // seconds * seconds, timezone.utc)


def bucket_points(rows, end, config):
    """Rows already contain bucket means, not interpolated readings."""
    rows = {timestamp(row['time']): row for row in rows}
    if not rows:
        return
    current = min(rows)
    while current < end:
        row = rows.get(current, {})
        yield AnalysisInput(current, row.get('vapor_temp'), row.get('raw_mv'), row.get('pt_raw_mv'),
                            sensor_invalid=bool(row.get('sensor_invalid', False)))
        current += timedelta(seconds=config.bucket_seconds)


class AnalysisService:
    def __init__(self, repository, config=AnalysisConfig(), analyzer_type=ProcessAnalyzer):
        self.repository = repository
        self.config = config
        self.analyzer_type = analyzer_type

    def rebuild(self, start, end):
        start, end = timestamp(start), timestamp(end)
        if start >= end:
            raise ValueError('from must precede to')
        # Never include an open bucket, even when the requested end lies in the future.
        cutoff = floor_bucket(min(end, datetime.now(timezone.utc)), self.config.bucket_seconds)
        # Baseline and CUSUM retain state beyond finite feature windows. Replay all
        # available history for exact agreement with an uninterrupted live analyzer.
        rows = self.repository.analysis_buckets(cutoff, self.config.bucket_seconds,
                                              self.config.valid_sensor_qualities)
        analyzer = self.analyzer_type(self.config)
        results = []
        for point in bucket_points(rows, cutoff, self.config):
            result = analyzer.update(point)
            if point.time >= start:
                results.append(result)
        self.repository.save_analysis(results, replace_range=(
            start, end, self.analyzer_type.detector_name, self.config.algo_version))
        return {'points_written': len(results),
                'detector_name': self.analyzer_type.detector_name, 'algo_version': self.config.algo_version,
                'completed_until': cutoff.isoformat()}

    def process_completed_bucket(self, analyzer, bucket_start):
        """Read only this bucket, using the same aggregation as historical replay."""
        start = timestamp(bucket_start)
        rows = self.repository.analysis_buckets(
            start + timedelta(seconds=self.config.bucket_seconds),
            self.config.bucket_seconds, self.config.valid_sensor_qualities, start=start)
        row = rows[0] if rows else {}
        point = AnalysisInput(start, row.get('vapor_temp'), row.get('raw_mv'),
                              row.get('pt_raw_mv'),
                              sensor_invalid=bool(row.get('sensor_invalid', False)))
        return self.save_completed_point(analyzer, point)

    def save_completed_point(self, analyzer, point):
        """Caller keeps one continuous analyzer and supplies completed UTC buckets.

        After restart, replay sensor history through the same engine before continuing.
        """
        if analyzer.config != self.config:
            raise ValueError('service and analyzer config must match')
        if floor_bucket(point.time, self.config.bucket_seconds) != point.time:
            raise ValueError('bucket must be aligned')
        if point.time + timedelta(seconds=self.config.bucket_seconds) > datetime.now(timezone.utc):
            raise ValueError('bucket is not complete')
        result = analyzer.update(point)
        self.repository.save_analysis([result])
        return result
