from dataclasses import replace, asdict
from datetime import datetime, timedelta, timezone
import math
import json
import pytest
from disti.process_analysis import AnalysisConfig, AnalysisInput, ProcessAnalyzer, ProcessState as S
from disti.process_analysis.service import AnalysisService, bucket_points
from disti.api import create_app

T=datetime(2026,1,1,tzinfo=timezone.utc)

def p(i,t=82,mv=100,pt=1000,rid=None,invalid=False):
    return AnalysisInput(T+timedelta(seconds=20*i),t,mv,pt,rid,invalid)

def fast(**changes):
    return replace(AnalysisConfig(),baseline_delay_seconds=0,baseline_warmup_samples=2,**changes)

def test_plateau_persistence_and_dt():
    a=ProcessAnalyzer()
    assert a.update(p(0)).process_state==S.AUFHEIZEN
    for i in (1,2):
        assert a.update(p(i)).process_state==S.AUFHEIZEN
    r=a.update(p(3))
    assert r.process_state==S.VORLAUF and r.features.dtdt==0
    assert a.plateau_time==p(3).time

def test_temperature_slope_and_time_windows():
    a=ProcessAnalyzer()
    for i in range(60):
        r=a.update(p(i,t=76+i/3,mv=50+i))
    assert r.features.dtdt==pytest.approx(1)
    assert r.features.raw_mv_1m==pytest.approx(108)
    assert r.features.raw_mv_5m==pytest.approx(102)
    assert r.features.running_min_5m==95
    assert r.features.rise_from_min_5m==14
    for key in ('trend_1m','trend_3m','trend_5m'):
        assert getattr(r.features,key)==pytest.approx(3)

def test_baseline_delay_and_no_forced_middle():
    a=ProcessAnalyzer()
    for i in range(18): r=a.update(p(i))
    assert r.details.baseline_samples==0
    r=a.update(p(18))
    assert r.details.baseline_samples==1
    for i in range(19,60): r=a.update(p(i))
    assert r.process_state==S.VORLAUF
    assert r.details.baseline_samples==42
    assert r.details.baseline_sigma==1.5

def test_ew_variance_and_sigma():
    a=ProcessAnalyzer(fast())
    for i in range(4): a.update(p(i))
    r=a.update(p(4,mv=102))
    alpha=1-0.5**(20/600)
    assert r.details.baseline_mu==pytest.approx(100+alpha*2)
    assert r.details.baseline_var==pytest.approx((1-alpha)*(4+alpha*4))

def test_freeze_z_cusum_hysteresis_temperature_gates():
    a=ProcessAnalyzer(fast())
    for i in range(5): a.update(p(i))
    r=a.update(p(5,t=85,mv=115))
    assert r.details.baseline_frozen
    assert r.details.baseline_mu==100
    assert r.details.z==pytest.approx(15/r.details.baseline_sigma)
    assert r.details.cusum_s==pytest.approx(r.details.z-.75)
    assert r.detector_alarm and r.process_state==S.NACHLAUF_ENTWICKELT
    prev=r.details.cusum_s
    r=a.update(p(6,t=86,mv=101))
    assert r.process_state==S.NACHLAUF_WAHRSCHEINLICH
    assert r.details.cusum_s==pytest.approx(.995*prev+r.details.z-.75)
    assert r.detector_score==min(r.details.cusum_s/6,2)
    r=a.update(p(7,t=86,mv=80))
    assert not r.detector_alarm and r.details.cusum_s==0

def test_warmup_and_detection_gate():
    a=ProcessAnalyzer()
    for i in range(20): r=a.update(p(i,t=84,mv=100))
    assert not r.detector_alarm and r.details.z is None
    a=ProcessAnalyzer(fast())
    for i in range(5): a.update(p(i))
    assert a.update(p(5,t=83,mv=120)).details.cusum_s==0

def test_gap_freezes_detector_and_breaks_plateau():
    a=ProcessAnalyzer(fast())
    for i in range(5): a.update(p(i))
    r=a.update(p(5,t=85,mv=115)); previous=asdict(r.details)
    r=a.update(p(7,t=86,mv=150))
    assert r.process_state==S.DATENLUECKE
    assert r.details.cusum_s==previous['cusum_s'] and r.details.baseline_mu==previous['baseline_mu']
    assert r.features.dtdt is None
    r=a.update(p(8,t=None))
    assert r.process_state==S.DATENLUECKE and not r.ended
    assert a.update(p(9,t=85)).features.dtdt is None

def test_invalid_duration_and_gap_interrupts_timer():
    a=ProcessAnalyzer()
    a.update(p(0))
    for i in range(1,10):
        assert a.update(p(i,mv=201)).process_state==S.SENSOR_UNGUELTIG
    assert a.update(p(10,mv=201)).process_state==S.ENDE
    assert not a.alarm and a.s==0
    a=ProcessAnalyzer();a.update(p(0))
    assert a.update(p(1,pt=3300)).process_state==S.SENSOR_UNGUELTIG
    assert a.update(p(9,pt=None)).process_state==S.DATENLUECKE
    assert a.update(p(10,pt=3300)).process_state==S.SENSOR_UNGUELTIG

@pytest.mark.parametrize('temperature',[74,80.5])
def test_end_restart_reset(temperature):
    a=ProcessAnalyzer();a.update(p(0))
    r=a.update(p(1,t=temperature))
    assert r.ended and r.process_state==S.ENDE and r.detector_score==0
    if temperature>=75:
        assert a.update(p(2)).process_state==S.ENDE
        a.update(p(3,t=74)); i=4
    else: i=2
    assert a.update(p(i)).process_state==S.AUFHEIZEN
    a.reset('new')
    assert a.last_time is None and a.mu is None and a.plateau_time is None
    assert a.update(p(0,rid='new')).process_state==S.AUFHEIZEN

def test_order_run_and_no_future():
    a=ProcessAnalyzer();prefix=[a.update(p(i,mv=100+i)) for i in range(5)]
    a.update(p(5,mv=180))
    b=ProcessAnalyzer()
    assert prefix==[b.update(p(i,mv=100+i)) for i in range(5)]
    with pytest.raises(ValueError): a.update(p(5))
    with pytest.raises(ValueError): a.update(p(6,rid='other'))
    with pytest.raises(ValueError): ProcessAnalyzer().update(replace(p(0),time=T.replace(tzinfo=None)))

def test_optional_strict_plateau():
    a=ProcessAnalyzer(replace(AnalysisConfig(),strict_plateau=True))
    for i in range(5): r=a.update(p(i,t=80))
    assert r.process_state==S.AUFHEIZEN

def test_missing_bucket_generation():
    rows=[{'time':T,'vapor_temp':82,'raw_mv':100,'pt_raw_mv':1000},
          {'time':T+timedelta(seconds=40),'vapor_temp':82,'raw_mv':100,'pt_raw_mv':1000}]
    points=list(bucket_points(rows,'run',T+timedelta(seconds=60),AnalysisConfig()))
    assert len(points)==3 and points[1].raw_mv is None

@pytest.fixture
def analysis_repo(repo):
    # Same additive schema, using SQLite types for portable persistence/API tests.
    from pathlib import Path
    sql=(Path(__file__).parents[1]/'migrations/004_process_analysis.sql').read_text()
    sql=sql.replace("jsonb NOT NULL DEFAULT '{}'::jsonb", "text NOT NULL DEFAULT '{}'")
    conn=repo.connection_factory();conn.executescript(sql);conn.close()
    return repo

def seed(repo, rid='11111111-1111-1111-1111-111111111111'):
    repo._execute("INSERT INTO distillation_runs(id,run_type,status,started_at) VALUES(%s,%s,%s,%s)",(rid,'other','completed',T.isoformat()),fetch=None)
    for sensor in ('vapor-temp','ec-1','ec-temp'): repo.ensure_sensor(sensor,sensor,'test')
    from disti.hardware.base import SensorReading
    for i in range(40):
        for sensor,value,mv in [('vapor-temp',82,None),('ec-1',1,100),('ec-temp',40,1000)]:
            repo.save_measurement(SensorReading(sensor,'temperature' if sensor!='ec-1' else 'conductivity',value,'test',timestamp=T+timedelta(seconds=20*i),raw_mv=mv),rid)
    return rid

def test_rebuild_idempotence_subrange_live_and_raw_immutable(analysis_repo):
    repo=analysis_repo;rid=seed(repo)
    before=repo.replay_measurements(rid)
    service=AnalysisService(repo)
    start,end=T,T+timedelta(seconds=800)
    assert service.rebuild(start,end,rid)['points_written']==40
    first=repo._execute('SELECT * FROM process_analysis ORDER BY time')
    service.rebuild(T+timedelta(seconds=600),end,rid)
    assert repo._execute('SELECT * FROM process_analysis ORDER BY time')==first
    assert repo.replay_measurements(rid)==before
    a=ProcessAnalyzer();a.reset(rid)
    results=[a.update(p(i,rid=rid)) for i in range(40)]
    assert json.loads(first[-1]['details'])==asdict(results[-1].details)
    assert service.save_completed_point(a,p(40,rid=rid)).time==p(40).time

def test_rebuild_route_validation_and_success(analysis_repo):
    rid=seed(analysis_repo);client=create_app(analysis_repo).test_client()
    for data in ({},[],{'from':T.isoformat(),'to':T.isoformat()}, {'from':'bad','to':'bad'}, {'from':T.isoformat(),'to':T.isoformat(),'algo_version':'future'}):
        assert client.post('/api/analysis/rebuild',json=data).status_code==400
    response=client.post('/api/analysis/rebuild',json={'from':T.isoformat(),'to':(T+timedelta(seconds=800)).isoformat(),'run_id':rid,'algo_version':'cusum-v1'})
    assert response.status_code==200 and response.json['points_written']==40

def test_nonfinite_and_quality_invalid(analysis_repo):
    a=ProcessAnalyzer()
    r=a.update(p(0,mv=math.nan))
    assert r.process_state==S.SENSOR_UNGUELTIG and r.raw_mv is None
    assert a.update(p(1,invalid=True)).process_state==S.SENSOR_UNGUELTIG
    rid=seed(analysis_repo)
    analysis_repo._execute("UPDATE sensor_measurements SET quality='simulated'",fetch=None)
    rows=analysis_repo.analysis_buckets(rid,T+timedelta(seconds=800),20)
    assert not rows[0]['sensor_invalid']
    analysis_repo._execute("UPDATE sensor_measurements SET quality='error' WHERE sensor_id='ec-1'",fetch=None)
    assert analysis_repo.analysis_buckets(rid,T+timedelta(seconds=800),20)[0]['sensor_invalid']

def test_baseline_frozen_is_latched_and_alarm_threshold_strict():
    a=ProcessAnalyzer(fast())
    for i in range(5): a.update(p(i))
    a.update(p(5,t=85))
    r=a.update(p(6,t=84,mv=120))
    assert r.details.baseline_mu==100 and r.details.baseline_frozen
    # Exactly representable sigma avoids a floating-point value just above h.
    a=ProcessAnalyzer(fast(sigma_min_mv=2.0))
    for i in range(5): a.update(p(i))
    sigma=max(math.sqrt(a.var),a.config.sigma_min_mv)
    r=a.update(p(5,t=85,mv=100+sigma*(6+.75)))
    assert r.details.cusum_s==pytest.approx(6) and not r.detector_alarm

def test_rebuild_separates_runs_and_excludes_partial_buckets(analysis_repo):
    rid=seed(analysis_repo)
    service=AnalysisService(analysis_repo)
    r=service.rebuild(T,T+timedelta(seconds=799))
    assert r['runs']==[rid] and r['points_written']==39
    other=seed(analysis_repo,'22222222-2222-2222-2222-222222222222')
    both=service.rebuild(T,T+timedelta(seconds=799))
    assert set(both['runs'])=={rid,other} and both['points_written']==78
    with pytest.raises(ValueError): service.rebuild(T,T+timedelta(seconds=800),'unknown')
    with pytest.raises(ValueError): service.save_completed_point(ProcessAnalyzer(),replace(p(0),time=T+timedelta(seconds=1)))

def test_exact_warmup_and_configured_z_clip():
    a=ProcessAnalyzer()
    for i in range(47): r=a.update(p(i))
    assert r.details.baseline_samples==29 and r.details.z is None
    r=a.update(p(47))
    assert r.details.baseline_samples==30 and r.details.z==0
    a=ProcessAnalyzer(fast(z_clip=1.0))
    for i in range(5): a.update(p(i))
    r=a.update(p(5,t=85,mv=150))
    assert r.details.z==1 and r.details.cusum_s==.25
    assert AnalysisConfig().z_clip is None

def test_baseline_uses_elapsed_buckets_without_gap_imputation():
    a=ProcessAnalyzer(fast())
    for i in range(5): a.update(p(i))
    mu,var,count=a.mu,a.var,a.baseline_samples
    assert a.update(p(20)).process_state==S.DATENLUECKE
    assert (a.mu,a.var,a.baseline_samples)==(mu,var,count)
    r=a.update(p(21,mv=102))
    alpha=1-0.5**(20/600)
    assert r.details.baseline_mu==pytest.approx(mu+alpha*(102-mu))
    assert r.features.raw_mv_1m==102 and r.features.trend_1m is None

def test_live_reads_one_bucket_and_matches_rebuild(analysis_repo):
    rid=seed(analysis_repo)
    service=AnalysisService(analysis_repo)
    analyzer=ProcessAnalyzer();analyzer.reset(rid)
    for i in range(40): service.process_completed_bucket(analyzer,p(i).time)
    live=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    assert service.rebuild(T,T+timedelta(seconds=800),rid)['points_written']==40
    assert live==analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    rows=analysis_repo.analysis_buckets(rid,T+timedelta(seconds=40),20,start=T+timedelta(seconds=20))
    assert len(rows)==1 and rows[0]['time']==p(1).time
    assert service.process_completed_bucket(analyzer,p(40).time).process_state==S.DATENLUECKE

def test_alarm_holds_between_on_and_off_thresholds():
    a=ProcessAnalyzer(fast(sigma_min_mv=2))
    for i in range(5): a.update(p(i))
    assert a.update(p(5,t=85,mv=115)).detector_alarm
    for i in range(6,9):
        r=a.update(p(i,t=85,mv=100))
        if 1.8 <= r.details.cusum_s <= 6:
            assert r.detector_alarm
    assert 1.8 < r.details.cusum_s < 6 and r.detector_alarm
    for i in range(9,20): r=a.update(p(i,t=85,mv=100))
    assert r.details.cusum_s==0 and not r.detector_alarm

@pytest.mark.parametrize('signal,trend,acceleration', [
    (lambda minutes: 50, 0, 0),
    (lambda minutes: 20 + .4*minutes, .4, 0),
    (lambda minutes: 20 + .025*minutes**2, None, .05),
    (lambda minutes: 100 - 2*minutes + .025*minutes**2, None, .05),
])
def test_smoothed_trend_dynamics(signal, trend, acceleration):
    a=ProcessAnalyzer()
    for i in range(90):
        r=a.update(p(i,mv=signal(i/3)))
    if trend is not None:
        assert r.features.trend_3m==pytest.approx(trend)
        assert r.features.trend_5m==pytest.approx(trend)
    elif signal(1)>signal(0):
        assert r.features.trend_3m>0 and r.features.trend_5m>0
    else:
        # A still-negative smoothed trend is recovering towards zero.
        assert r.features.trend_3m<0 and r.features.trend_5m<0
    assert r.features.trend_accel_3m==pytest.approx(acceleration,abs=1e-10)
    assert r.features.trend_accel_5m==pytest.approx(acceleration,abs=1e-10)


def test_trend_dynamics_require_full_windows_and_reset_after_gaps():
    a=ProcessAnalyzer()
    for i in range(27):
        assert a.update(p(i)).features.trend_accel_3m is None
    assert a.update(p(27)).features.trend_accel_3m==0
    for i in range(28,33):
        assert a.update(p(i)).features.trend_accel_5m is None
    assert a.update(p(33)).features.trend_accel_5m==0
    assert a.update(p(34,mv=None)).features.trend_accel_3m is None
    for i in range(35,62):
        assert a.update(p(i)).features.trend_accel_3m is None
    assert a.update(p(62)).features.trend_accel_3m==0
    # Also guard time gaps when FeatureCalculator is used directly.
    from disti.process_analysis.features import FeatureCalculator
    f=FeatureCalculator(AnalysisConfig())
    for i in range(40): f.update(p(i))
    assert f.update(p(41)).trend_accel_3m is None


def test_trend_dynamics_are_causal_and_diagnostic_only():
    a,b=ProcessAnalyzer(fast()),ProcessAnalyzer(fast())
    from disti.process_analysis.features import FeatureCalculator
    class DifferentDiagnostics(FeatureCalculator):
        def update(self, point):
            return replace(super().update(point),trend_1m=999,trend_3m=-999,
                           trend_5m=999,trend_accel_3m=-999,trend_accel_5m=999)
    b.features=DifferentDiagnostics(b.config)
    prefix=[]
    for i in range(50):
        point=p(i,t=82 if i<20 else 85,mv=100 if i<25 else 115)
        normal,altered=a.update(point),b.update(point)
        assert normal.details==altered.details
        assert (normal.detector_score,normal.detector_alarm,normal.process_state,normal.ended)==(altered.detector_score,altered.detector_alarm,altered.process_state,altered.ended)
        prefix.append(normal)
    a.update(p(50,t=85,mv=190))
    replay=ProcessAnalyzer(fast())
    assert prefix==[replay.update(p(i,t=82 if i<20 else 85,mv=100 if i<25 else 115)) for i in range(50)]


def test_trend_dynamics_persisted_identically_in_live_and_rebuild(analysis_repo):
    rid=seed(analysis_repo)
    for i in range(40):
        analysis_repo._execute("UPDATE sensor_measurements SET raw_mv=%s WHERE run_id=%s AND sensor_id='ec-1' AND time=%s",
                               (20+.025*(i/3)**2,rid,p(i).time.isoformat()),fetch=None)
    service=AnalysisService(analysis_repo)
    a=ProcessAnalyzer();a.reset(rid)
    for i in range(40): service.process_completed_bucket(a,p(i).time)
    live=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    assert live[-1]['trend_accel_3m']==pytest.approx(.05)
    assert live[-1]['trend_accel_5m']==pytest.approx(.05)
    assert live[0]['trend_accel_3m'] is None
    assert 'trend_accel_3m' not in json.loads(live[-1]['details'])
    service.rebuild(T,T+timedelta(seconds=800),rid)
    assert live==analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
