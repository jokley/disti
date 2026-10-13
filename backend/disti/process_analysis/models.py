from dataclasses import dataclass
from datetime import datetime
from .states import ProcessState

@dataclass(frozen=True)
class AnalysisInput:
    time: datetime
    vapor_temp: float | None
    raw_mv: float | None
    pt_raw_mv: float | None
    sensor_invalid: bool = False

@dataclass(frozen=True)
class Features:
    dtdt: float | None = None
    raw_mv_1m: float | None = None
    raw_mv_5m: float | None = None
    running_min_5m: float | None = None
    rise_from_min_5m: float | None = None
    trend_1m: float | None = None
    trend_3m: float | None = None
    trend_5m: float | None = None
    trend_accel_3m: float | None = None
    trend_accel_5m: float | None = None
    ec_plateau_ref: float | None = None
    ec_drop_from_plateau: float | None = None
    ec_min_since_plateau: float | None = None
    ec_recovery_from_min: float | None = None

@dataclass(frozen=True)
class DetectorDetails:
    baseline_mu: float | None
    baseline_var: float | None
    baseline_sigma: float | None
    baseline_samples: int
    baseline_frozen: bool
    z: float | None
    cusum_s: float
    seconds_since_plateau: float | None

@dataclass(frozen=True)
class AnalysisResult:
    time: datetime
    vapor_temp: float | None
    raw_mv: float | None
    pt_raw_mv: float | None
    features: Features
    detector_name: str
    algo_version: str
    detector_score: float
    detector_alarm: bool
    process_state: ProcessState
    ended: bool
    details: DetectorDetails
