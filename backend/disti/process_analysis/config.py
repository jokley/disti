"""Experimental parameters; changes require a new algorithm version for comparison."""
from dataclasses import dataclass

@dataclass(frozen=True)
class AnalysisConfig:
    bucket_seconds: int = 20
    start_temperature: float = 75.0
    temperature_window_seconds: int = 60
    plateau_dtdt_max: float = 1.0
    plateau_persistence: int = 3
    strict_plateau: bool = False
    strict_plateau_temperature: float = 81.8
    strict_plateau_dtdt_min: float = -0.2
    strict_plateau_dtdt_max: float = 0.3
    baseline_delay_seconds: int = 300
    baseline_half_life_seconds: int = 600
    baseline_warmup_samples: int = 30
    initial_variance: float = 4.0
    sigma_min_mv: float = 1.5
    baseline_freeze_temperature: float = 84.5
    detection_temperature: float = 84.0
    probable_tail_temperature: float = 86.0
    cusum_k: float = 0.75
    cusum_h: float = 8.0
    cusum_leak: float = 0.995
    score_max: float = 2.0
    z_clip: float | None = None
    end_temperature_drop: float = 1.5
    invalid_sensor_duration_seconds: int = 180
    valid_sensor_qualities: tuple[str, ...] = ('good', 'simulated')
    ec_max_mv: float = 200.0
    pt_disconnect_mv: float = 3300.0
    pt_disconnect_tolerance_mv: float = 100.0
    feature_windows_seconds: tuple[int, int, int] = (60, 180, 300)
    trend_accel_lag_seconds: int = 60
    heating_start_dtdt_min: float = 0.20
    heating_start_persistence_seconds: int = 60
    cooling_dtdt_max: float = -0.50
    cooling_persistence_seconds: int = 60
    cooling_temperature_drop: float = 2.0
    cooling_peak_window_seconds: int = 300
    ready_window_seconds: int = 180
    ready_median_abs_dtdt_max: float = 0.10
    ready_bucket_abs_dtdt_max: float = 0.20
    ready_required_fraction: float = 0.80
    heating_detect_dtdt_min: float = 1.0
    vorlauf_start_dtdt_max: float = 0.30
    vorlauf_start_persistence_seconds: int = 40
    vorlauf_ausklang_window_seconds: int = 120
    vorlauf_ausklang_median_abs_dtdt_max: float = 0.12
    vorlauf_ausklang_bucket_abs_dtdt_max: float = 0.20
    vorlauf_ausklang_required_fraction: float = 0.80
    vorlauf_middle_confirm_seconds: int = 90
    algo_version: str = 'cusum-v1'

    @property
    def cusum_alarm_off(self) -> float:
        return 0.3 * self.cusum_h

    def __post_init__(self):
        if self.bucket_seconds <= 0 or self.baseline_half_life_seconds <= 0 or self.sigma_min_mv <= 0:
            raise ValueError('time scales and sigma must be positive')
        if not 0 <= self.cusum_leak <= 1 or not 0 <= self.cusum_alarm_off < self.cusum_h:
            raise ValueError('invalid CUSUM parameters')
        if self.plateau_persistence < 1 or self.baseline_warmup_samples < 1:
            raise ValueError('persistence and warmup must be positive')
        if self.vorlauf_start_persistence_seconds < 0 or self.vorlauf_middle_confirm_seconds < 0:
            raise ValueError('heads persistence must be nonnegative')
        if self.vorlauf_ausklang_window_seconds <= 0:
            raise ValueError('heads window must be positive')
        if not 0 <= self.vorlauf_ausklang_required_fraction <= 1:
            raise ValueError('heads fraction must be between zero and one')
        if self.heating_start_dtdt_min <= 0 or self.cooling_dtdt_max >= 0:
            raise ValueError('lifecycle gradients must have the expected sign')
        if min(self.heating_start_persistence_seconds, self.cooling_persistence_seconds) < 0:
            raise ValueError('lifecycle persistence must be nonnegative')
        if min(self.cooling_temperature_drop, self.cooling_peak_window_seconds, self.ready_window_seconds) <= 0:
            raise ValueError('lifecycle windows and drop must be positive')
        if not 0 <= self.ready_required_fraction <= 1:
            raise ValueError('ready fraction must be between zero and one')
