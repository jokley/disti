"""Causal time windows and smoothed diagnostic trend dynamics."""
from collections import deque
from datetime import timedelta
from statistics import fmean
from .models import AnalysisInput, Features

class FeatureCalculator:
    def __init__(self, config):
        self.config = config
        self.points = deque()
        self.trend_history = deque()
        self.contiguous_start = None

    def reset(self):
        self.points.clear()
        self.trend_history.clear()
        self.contiguous_start = None

    @staticmethod
    def slope(points):
        if len(points) < 2:
            return None
        times = [(t - points[0][0]).total_seconds() / 60 for t, _ in points]
        values = [v for _, v in points]
        mt, mv = fmean(times), fmean(values)
        denominator = sum((t - mt)**2 for t in times)
        return sum((t - mt)*(v - mv) for t, v in zip(times, values)) / denominator if denominator else None

    def update(self, point: AnalysisInput) -> Features:
        if self.points and (point.time-self.points[-1].time).total_seconds() != self.config.bucket_seconds:
            self.reset()
        if self.contiguous_start is None:
            self.contiguous_start = point.time
        self.points.append(point)
        longest = max(*self.config.feature_windows_seconds, self.config.temperature_window_seconds)
        while (point.time - self.points[0].time).total_seconds() >= longest:
            self.points.popleft()
        def window(seconds):
            return [p for p in self.points if (point.time-p.time).total_seconds() < seconds]
        short_seconds, medium_seconds, long_seconds = self.config.feature_windows_seconds
        short, long = window(short_seconds), window(long_seconds)
        temp = [(p.time, p.vapor_temp) for p in window(self.config.temperature_window_seconds)]
        minimum = min(p.raw_mv for p in long)
        smoothed = fmean(p.raw_mv for p in long)
        # Partial means remain visible, but diagnostic derivatives need a full
        # contiguous smoothing window and exact time lags. Never interpolate.
        full_mean = smoothed if (point.time-self.contiguous_start).total_seconds() >= long_seconds else None
        history = {time: (mean, trends) for time, mean, trends in self.trend_history}
        trends, accelerations = [], []
        for index, seconds in enumerate((medium_seconds, long_seconds)):
            previous_mean = history.get(point.time-timedelta(seconds=seconds), (None, None))[0]
            trend = (full_mean-previous_mean)/(seconds/60) if full_mean is not None and previous_mean is not None else None
            previous = history.get(point.time-timedelta(seconds=self.config.trend_accel_lag_seconds))
            previous_trend = previous[1][index] if previous else None
            accel = (trend-previous_trend)/(self.config.trend_accel_lag_seconds/60) if trend is not None and previous_trend is not None else None
            trends.append(trend)
            accelerations.append(accel)
        self.trend_history.append((point.time, full_mean, tuple(trends)))
        retention = max(medium_seconds, long_seconds, self.config.trend_accel_lag_seconds)
        while (point.time-self.trend_history[0][0]).total_seconds() > retention:
            self.trend_history.popleft()
        return Features(
            dtdt=self.slope(temp), raw_mv_1m=fmean(p.raw_mv for p in short),
            raw_mv_5m=smoothed, running_min_5m=minimum,
            rise_from_min_5m=point.raw_mv-minimum,
            trend_1m=self.slope([(p.time, p.raw_mv) for p in short]),
            trend_3m=trends[0], trend_5m=trends[1],
            trend_accel_3m=accelerations[0], trend_accel_5m=accelerations[1])
