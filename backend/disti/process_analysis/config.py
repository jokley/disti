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
    vorlauf_ausklang_drop_mv: float = 1.0
    vorlauf_ausklang_persistence_seconds: int = 40
    vorlauf_middle_drop_mv: float = 2.0
    vorlauf_middle_recovery_mv: float = 0.4
    vorlauf_middle_persistence_seconds: int = 40
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
        if self.vorlauf_ausklang_persistence_seconds < 0 or self.vorlauf_middle_persistence_seconds < 0:
            raise ValueError('heads persistence must be nonnegative')
