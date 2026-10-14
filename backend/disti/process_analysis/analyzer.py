"""Database-free incremental process interpretation. One result per input."""
import math
from collections import deque
from statistics import median
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
        self._reset_heads()
        self.process_state = State.BEREIT
        self.recent_temperatures = deque()
        self.quiet_gradients = deque()
        self._break_lifecycle_persistence()

    def _start(self):
        self.active, self.ended = True, False
        self.tmax = self.plateau_time = None
        self.plateau_count = self.baseline_samples = 0
        self.mu = self.var = None
        self.baseline_frozen = False
        self.s, self.alarm = 0.0, False
        self.features.reset()
        self._reset_heads()

    def _end(self):
        self.active, self.ended, self.restart_armed = False, True, False
        self.s, self.alarm = 0.0, False
        self._reset_heads()

    def _reset_heads(self):
        self.heads_state = State.AUFHEIZEN
        self.heating_seen = False
        self.ec_plateau_ref = self.ec_min_since_plateau = None
        self.heads_dtdt = deque()
        self._break_heads_persistence()

    def _break_heads_persistence(self):
        self.heads_start_since = self.heads_middle_since = None
        self.heads_contiguous_start = None
        self.heads_dtdt.clear()

    def _heads_state(self, time, features):
        """Temperature dynamics only; baseline plateau/CUSUM stay independent."""
        c = self.config
        if self.heads_state == State.MITTELLAUF:
            return self.heads_state
        slope = features.dtdt
        if slope is None:
            self._break_heads_persistence()
            return self.heads_state
        if self.heads_contiguous_start is None:
            self.heads_contiguous_start = time
        self.heads_dtdt.append((time, abs(slope)))
        while (time-self.heads_dtdt[0][0]).total_seconds() >= c.vorlauf_ausklang_window_seconds:
            self.heads_dtdt.popleft()
        if slope >= c.heating_detect_dtdt_min:
            self.heating_seen = True
        if self.heads_state == State.AUFHEIZEN:
            if not self.heating_seen or slope > c.vorlauf_start_dtdt_max:
                self.heads_start_since = None
            else:
                if self.heads_start_since is None:
                    self.heads_start_since = time
                if (time-self.heads_start_since).total_seconds() >= c.vorlauf_start_persistence_seconds:
                    self.heads_state = State.VORLAUF
                    self.heads_start_since = None
            return self.heads_state
        values = [value for _, value in self.heads_dtdt]
        stable = ((time-self.heads_contiguous_start).total_seconds() >= c.vorlauf_ausklang_window_seconds and
                  median(values) <= c.vorlauf_ausklang_median_abs_dtdt_max and
                  sum(value <= c.vorlauf_ausklang_bucket_abs_dtdt_max for value in values)/len(values)
                  >= c.vorlauf_ausklang_required_fraction)
        if self.heads_state == State.VORLAUF:
            if stable:
                self.heads_state = State.VORLAUF_AUSKLANG
                self.heads_middle_since = time
        elif not stable:
            self.heads_middle_since = None
        else:
            if self.heads_middle_since is None:
                self.heads_middle_since = time
            if (time-self.heads_middle_since).total_seconds() >= c.vorlauf_middle_confirm_seconds:
                self.heads_state = State.MITTELLAUF
                self.heads_middle_since = None
        return self.heads_state

    def _break_lifecycle_persistence(self):
        self.heating_since = self.cooling_since = self.quiet_since = None
        self.recent_temperatures.clear()
        self.quiet_gradients.clear()

    def _quiet_ready(self, time, slope):
        c = self.config
        if self.quiet_since is None:
            self.quiet_since = time
        self.quiet_gradients.append((time, abs(slope)))
        while (time-self.quiet_gradients[0][0]).total_seconds() >= c.ready_window_seconds:
            self.quiet_gradients.popleft()
        values = [value for _, value in self.quiet_gradients]
        return ((time-self.quiet_since).total_seconds() >= c.ready_window_seconds and
                median(values) <= c.ready_median_abs_dtdt_max and
                sum(value <= c.ready_bucket_abs_dtdt_max for value in values)/len(values)
                >= c.ready_required_fraction)

    def _lifecycle_state(self, point, features, detector_state):
        """Physical operating phase; the detector keeps its existing lifecycle."""
        c, time, slope = self.config, point.time, features.dtdt
        self.recent_temperatures.append((time, point.vapor_temp))
        while (time-self.recent_temperatures[0][0]).total_seconds() >= c.cooling_peak_window_seconds:
            self.recent_temperatures.popleft()
        if slope is None:
            self.heating_since = self.cooling_since = self.quiet_since = None
            self.quiet_gradients.clear()
            return self.process_state
        if self.process_state == State.ABKUEHLEN:
            if self._quiet_ready(time, slope):
                self.process_state = State.BEREIT
                self._break_lifecycle_persistence()
            return self.process_state
        if self.process_state == State.NACHLAUF:
            drop = max(temp for _, temp in self.recent_temperatures)-point.vapor_temp
            if slope <= c.cooling_dtdt_max:
                if self.cooling_since is None:
                    self.cooling_since = time
                if ((time-self.cooling_since).total_seconds() >= c.cooling_persistence_seconds and
                        drop >= c.cooling_temperature_drop):
                    self.process_state = State.ABKUEHLEN
                    self.quiet_since = None
                    self.quiet_gradients.clear()
            else:
                self.cooling_since = None
            return self.process_state
        if detector_state in (State.NACHLAUF_ENTWICKELT, State.NACHLAUF):
            self.process_state = detector_state
        elif self.process_state == State.BEREIT:
            if slope > c.heating_start_dtdt_min:
                if self.heating_since is None:
                    self.heating_since = time
                if (time-self.heating_since).total_seconds() >= c.heating_start_persistence_seconds:
                    self.process_state = State.AUFHEIZEN
                    self.heating_since = None
            else:
                self.heating_since = None
        elif detector_state in (State.VORLAUF, State.VORLAUF_AUSKLANG, State.MITTELLAUF):
            self.process_state = detector_state
        return self.process_state

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
            self._break_heads_persistence()
            self._break_lifecycle_persistence()
            self.features.reset()
            self.plateau_count = 0
            self.invalid_since = None
            state = State.DATENLUECKE
        elif invalid:
            self._break_heads_persistence()
            self._break_lifecycle_persistence()
            self.features.reset()
            self.plateau_count = 0
            if self.invalid_since is None:
                self.invalid_since = point.time
            if self.active and (point.time-self.invalid_since).total_seconds() >= c.invalid_sensor_duration_seconds:
                self._end()
            state = State.SENSOR_UNGUELTIG
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
            state = State.BEREIT
            if self.active:
                self.tmax = max(t, self.tmax if self.tmax is not None else t)
                plateau = f.dtdt is not None and t >= c.start_temperature and f.dtdt < c.plateau_dtdt_max
                if c.strict_plateau:
                    plateau = f.dtdt is not None and t >= c.strict_plateau_temperature and c.strict_plateau_dtdt_min <= f.dtdt <= c.strict_plateau_dtdt_max
                self.plateau_count = self.plateau_count+1 if plateau else 0
                if self.plateau_time is None and self.plateau_count >= c.plateau_persistence:
                    self.plateau_time = point.time
                if self.plateau_time is not None:
                    f = FeatureCalculator.relative_to_plateau(f, self.ec_plateau_ref, self.ec_min_since_plateau)
                    self.ec_plateau_ref, self.ec_min_since_plateau = f.ec_plateau_ref, f.ec_min_since_plateau
                state = self._heads_state(point.time, f)
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
                    state = State.NACHLAUF if t >= c.probable_tail_temperature else State.NACHLAUF_ENTWICKELT
            state = self._lifecycle_state(point, f, state)
        sigma = max(math.sqrt(self.var), c.sigma_min_mv) if self.var is not None else None
        details = DetectorDetails(self.mu, self.var, sigma, self.baseline_samples, self.baseline_frozen, z, self.s,
                                  (point.time-self.plateau_time).total_seconds() if self.plateau_time else None)
        physical = tuple(v if v is None or math.isfinite(v) else None for v in values)
        return AnalysisResult(point.time, *physical, f,
                              self.detector_name, c.algo_version, min(self.s/c.cusum_h, c.score_max), self.alarm, state, self.ended, details)
