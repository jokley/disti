"""Database-free incremental process interpretation. One result per input."""
import math
from .config import AnalysisConfig
from .features import FeatureCalculator
from .models import AnalysisInput, AnalysisResult, Features, DetectorDetails
from .states import ProcessState as State

class ProcessAnalyzer:
    detector_name = 'cusum'

    def __init__(self, config: AnalysisConfig = AnalysisConfig()):
        self.config = config
        self.reset()

    def reset(self) -> None:
        self.last_time = None
        self.active = False
        self.ended = False
        self.restart_armed = True
        self.tmax = None
        self.plateau_time = None
        self.plateau_count = 0
        self.invalid_since = None
        self.mu = self.var = None
        self.baseline_samples = 0
        self.baseline_frozen = False
        self.s = 0.0
        self.alarm = False
        self.features = FeatureCalculator(self.config)

    def _start(self):
        self.active, self.ended = True, False
        self.tmax = self.plateau_time = None
        self.plateau_count = self.baseline_samples = 0
        self.mu = self.var = None
        self.baseline_frozen = False
        self.s, self.alarm = 0.0, False
        self.features.reset()

    def _end(self):
        self.active, self.ended, self.restart_armed = False, True, False
        self.s, self.alarm = 0.0, False

    def update(self, point: AnalysisInput) -> AnalysisResult:
        c = self.config
        if point.time.tzinfo is None:
            raise ValueError('timezone-aware timestamps required')
        if self.last_time is not None and point.time <= self.last_time:
            raise ValueError('inputs must be strictly chronological')
        gap = self.last_time is not None and (point.time-self.last_time).total_seconds() != c.bucket_seconds
        self.last_time = point.time
        f, z = Features(), None
        values = (point.vapor_temp, point.raw_mv, point.pt_raw_mv)
        missing = any(v is None for v in values)
        invalid = point.sensor_invalid or any(v is not None and not math.isfinite(v) for v in values)
        invalid |= point.raw_mv is not None and point.raw_mv > c.ec_max_mv
        invalid |= point.pt_raw_mv is not None and abs(point.pt_raw_mv-c.pt_disconnect_mv) <= c.pt_disconnect_tolerance_mv
        if gap or missing:
            self.features.reset()
            self.plateau_count = 0
            self.invalid_since = None
            state = State.ENDE if self.ended else State.DATENLUECKE
        elif invalid:
            self.features.reset()
            self.plateau_count = 0
            if self.invalid_since is None:
                self.invalid_since = point.time
            if self.active and (point.time-self.invalid_since).total_seconds() >= c.invalid_sensor_duration_seconds:
                self._end()
            state = State.ENDE if self.ended else State.SENSOR_UNGUELTIG
        else:
            self.invalid_since = None
            t = point.vapor_temp
            if t < c.start_temperature:
                self.restart_armed = True
            if not self.active and self.restart_armed and t >= c.start_temperature:
                self._start()
            if self.active and (t < c.start_temperature or (self.tmax is not None and self.tmax-t >= c.end_temperature_drop)):
                self._end()
                if t < c.start_temperature:
                    self.restart_armed = True
            f = self.features.update(point)
            state = State.ENDE if self.ended else State.IDLE
            if self.active:
                self.tmax = max(t, self.tmax if self.tmax is not None else t)
                plateau = f.dtdt is not None and t >= c.start_temperature and f.dtdt < c.plateau_dtdt_max
                if c.strict_plateau:
                    plateau = f.dtdt is not None and t >= c.strict_plateau_temperature and c.strict_plateau_dtdt_min <= f.dtdt <= c.strict_plateau_dtdt_max
                self.plateau_count = self.plateau_count+1 if plateau else 0
                if self.plateau_time is None and self.plateau_count >= c.plateau_persistence:
                    self.plateau_time = point.time
                state = State.VORLAUF if self.plateau_time else State.AUFHEIZEN
                if t >= c.baseline_freeze_temperature:
                    self.baseline_frozen = True
                ready_time = self.plateau_time is not None and (point.time-self.plateau_time).total_seconds() >= c.baseline_delay_seconds
                if ready_time and not self.baseline_frozen:
                    if self.mu is None:
                        self.mu, self.var = point.raw_mv, c.initial_variance
                    else:
                        alpha = 1 - 0.5**(c.bucket_seconds/c.baseline_half_life_seconds)
                        delta = point.raw_mv-self.mu
                        self.mu += alpha*delta
                        self.var = (1-alpha)*(self.var+alpha*delta*delta)
                    self.baseline_samples += 1
                if self.mu is not None and self.baseline_samples >= c.baseline_warmup_samples:
                    z = (point.raw_mv-self.mu)/max(math.sqrt(self.var), c.sigma_min_mv)
                    if c.z_clip is not None:
                        z = max(-c.z_clip, min(z, c.z_clip))
                    if t >= c.detection_temperature:
                        self.s = max(0.0, c.cusum_leak*self.s+z-c.cusum_k)
                        if self.s > c.cusum_h:
                            self.alarm = True
                        elif self.s < c.cusum_alarm_off:
                            self.alarm = False
                if self.alarm:
                    state = State.NACHLAUF_WAHRSCHEINLICH if t >= c.probable_tail_temperature else State.NACHLAUF_ENTWICKELT
        sigma = max(math.sqrt(self.var), c.sigma_min_mv) if self.var is not None else None
        details = DetectorDetails(self.mu, self.var, sigma, self.baseline_samples, self.baseline_frozen, z, self.s,
                                  (point.time-self.plateau_time).total_seconds() if self.plateau_time else None)
        physical = tuple(v if v is None or math.isfinite(v) else None for v in values)
        return AnalysisResult(point.time, *physical, f,
                              self.detector_name, c.algo_version, min(self.s/c.cusum_h, c.score_max), self.alarm, state, self.ended, details)
