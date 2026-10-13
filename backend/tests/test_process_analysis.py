from dataclasses import replace, asdict
from datetime import datetime, timedelta, timezone
import math
import json
import pytest
from disti.process_analysis import AnalysisConfig, AnalysisInput, ProcessAnalyzer, ProcessState as S
from disti.process_analysis.service import AnalysisService, bucket_points
from disti.api import create_app

T=datetime(2026,1,1,tzinfo=timezone.utc)

def p(i,t=82,mv=100,pt=1000,invalid=False):
    return AnalysisInput(T+timedelta(seconds=20*i),t,mv,pt,invalid)

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
    r=a.update(p(5,t=85,mv=120))
    assert r.details.baseline_frozen
    assert r.details.baseline_mu==100
    assert r.details.z==pytest.approx(20/r.details.baseline_sigma)
    assert r.details.cusum_s==pytest.approx(r.details.z-.75)
    assert r.detector_alarm and r.process_state==S.NACHLAUF_ENTWICKELT
    prev=r.details.cusum_s
    r=a.update(p(6,t=86,mv=101))
    assert r.process_state==S.NACHLAUF_WAHRSCHEINLICH
    assert r.details.cusum_s==pytest.approx(.995*prev+r.details.z-.75)
    assert r.detector_score==min(r.details.cusum_s/8,2)
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
    a.reset()
    assert a.last_time is None and a.mu is None and a.plateau_time is None
    assert a.update(p(0)).process_state==S.AUFHEIZEN

def test_order_and_no_future():
    a=ProcessAnalyzer();prefix=[a.update(p(i,mv=100+i)) for i in range(5)]
    a.update(p(5,mv=180))
    b=ProcessAnalyzer()
    assert prefix==[b.update(p(i,mv=100+i)) for i in range(5)]
    with pytest.raises(ValueError): a.update(p(5))
    with pytest.raises(ValueError): ProcessAnalyzer().update(replace(p(0),time=T.replace(tzinfo=None)))

def test_optional_strict_plateau():
    a=ProcessAnalyzer(replace(AnalysisConfig(),strict_plateau=True))
    for i in range(5): r=a.update(p(i,t=80))
    assert r.process_state==S.AUFHEIZEN

def test_missing_bucket_generation():
    rows=[{'time':T,'vapor_temp':82,'raw_mv':100,'pt_raw_mv':1000},
          {'time':T+timedelta(seconds=40),'vapor_temp':82,'raw_mv':100,'pt_raw_mv':1000}]
    points=list(bucket_points(rows,T+timedelta(seconds=60),AnalysisConfig()))
    assert len(points)==3 and points[1].raw_mv is None

@pytest.fixture
def analysis_repo(repo):
    # Same additive schema, using SQLite types for portable persistence/API tests.
    from pathlib import Path
    sql=(Path(__file__).parents[1]/'migrations/004_process_analysis.sql').read_text()
    sql=sql.replace("jsonb NOT NULL DEFAULT '{}'::jsonb", "text NOT NULL DEFAULT '{}'")
    conn=repo.connection_factory();conn.executescript(sql);conn.close()
    return repo

def seed(repo, rid=None):
    if rid is not None:
        repo._execute("INSERT INTO distillation_runs(id,run_type,status,started_at) VALUES(%s,%s,%s,%s)",(rid,'other','completed',T.isoformat()),fetch=None)
    for sensor in ('vapor-temp','ec-1','ec-temp'): repo.ensure_sensor(sensor,sensor,'test')
    from disti.hardware.base import SensorReading
    for i in range(40):
        for sensor,value,mv in [('vapor-temp',82,None),('ec-1',1,100),('ec-temp',40,1000)]:
            repo.save_measurement(SensorReading(sensor,'temperature' if sensor!='ec-1' else 'conductivity',value,'test',timestamp=T+timedelta(seconds=20*i),raw_mv=mv),rid)
    return rid

def test_rebuild_idempotence_subrange_live_and_raw_immutable(analysis_repo):
    repo=analysis_repo;rid=seed(repo)
    before=repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')
    service=AnalysisService(repo)
    start,end=T,T+timedelta(seconds=800)
    assert service.rebuild(start,end)['points_written']==40
    first=repo._execute('SELECT * FROM process_analysis ORDER BY time')
    service.rebuild(T+timedelta(seconds=600),end)
    assert repo._execute('SELECT * FROM process_analysis ORDER BY time')==first
    assert repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')==before
    a=ProcessAnalyzer()
    results=[a.update(p(i)) for i in range(40)]
    assert json.loads(first[-1]['details'])==asdict(results[-1].details)
    assert service.save_completed_point(a,p(40)).time==p(40).time

def test_rebuild_route_validation_and_success(analysis_repo):
    rid=seed(analysis_repo);client=create_app(analysis_repo).test_client()
    for data in ({},[],{'from':T.isoformat(),'to':T.isoformat()}, {'from':'bad','to':'bad'}, {'from':T.isoformat(),'to':T.isoformat(),'algo_version':'future'}):
        assert client.post('/api/analysis/rebuild',json=data).status_code==400
    response=client.post('/api/analysis/rebuild',json={'from':T.isoformat(),'to':(T+timedelta(seconds=800)).isoformat(),'algo_version':'cusum-v1'})
    assert response.status_code==200 and response.json['points_written']==40

def test_nonfinite_and_quality_invalid(analysis_repo):
    a=ProcessAnalyzer()
    r=a.update(p(0,mv=math.nan))
    assert r.process_state==S.SENSOR_UNGUELTIG and r.raw_mv is None
    assert a.update(p(1,invalid=True)).process_state==S.SENSOR_UNGUELTIG
    rid=seed(analysis_repo)
    analysis_repo._execute("UPDATE sensor_measurements SET quality='simulated'",fetch=None)
    rows=analysis_repo.analysis_buckets(T+timedelta(seconds=800),20)
    assert not rows[0]['sensor_invalid']
    analysis_repo._execute("UPDATE sensor_measurements SET quality='error' WHERE sensor_id='ec-1'",fetch=None)
    assert analysis_repo.analysis_buckets(T+timedelta(seconds=800),20)[0]['sensor_invalid']

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
    r=a.update(p(5,t=85,mv=100+sigma*(8+.75)))
    assert r.details.cusum_s==pytest.approx(8) and not r.detector_alarm

def test_rebuild_ignores_run_assignments_and_excludes_partial_buckets(analysis_repo):
    seed(analysis_repo)
    service=AnalysisService(analysis_repo)
    r=service.rebuild(T,T+timedelta(seconds=799))
    assert r['points_written']==39 and 'runs' not in r
    # Assigned readings and NULL readings share one temporal series, never
    # reset or duplicate analysis simply because an acquisition run changes.
    seed(analysis_repo,'22222222-2222-2222-2222-222222222222')
    both=service.rebuild(T,T+timedelta(seconds=799))
    assert both['points_written']==39
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
    analyzer=ProcessAnalyzer()
    for i in range(40): service.process_completed_bucket(analyzer,p(i).time)
    live=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    assert service.rebuild(T,T+timedelta(seconds=800))['points_written']==40
    assert live==analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    rows=analysis_repo.analysis_buckets(T+timedelta(seconds=40),20,start=T+timedelta(seconds=20))
    assert len(rows)==1 and rows[0]['time']==p(1).time
    assert service.process_completed_bucket(analyzer,p(40).time).process_state==S.DATENLUECKE

def test_alarm_holds_between_on_and_off_thresholds():
    a=ProcessAnalyzer(fast(sigma_min_mv=2))
    for i in range(5): a.update(p(i))
    assert a.update(p(5,t=85,mv=120)).detector_alarm
    for i in range(6,13):
        r=a.update(p(i,t=85,mv=100))
        if 2.4 <= r.details.cusum_s <= 8:
            assert r.detector_alarm
    assert 2.4 < r.details.cusum_s < 8 and r.detector_alarm
    for i in range(13,30): r=a.update(p(i,t=85,mv=100))
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


def test_trend_dynamics_are_causal_and_do_not_affect_cusum():
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
        assert (normal.detector_score,normal.detector_alarm,normal.ended)==(altered.detector_score,altered.detector_alarm,altered.ended)
        prefix.append(normal)
    a.update(p(50,t=85,mv=190))
    replay=ProcessAnalyzer(fast())
    assert prefix==[replay.update(p(i,t=82 if i<20 else 85,mv=100 if i<25 else 115)) for i in range(50)]


def test_trend_dynamics_persisted_identically_in_live_and_rebuild(analysis_repo):
    rid=seed(analysis_repo)
    for i in range(40):
        analysis_repo._execute("UPDATE sensor_measurements SET raw_mv=%s WHERE sensor_id='ec-1' AND time=%s",
                               (20+.025*(i/3)**2,p(i).time.isoformat()),fetch=None)
    service=AnalysisService(analysis_repo)
    a=ProcessAnalyzer()
    for i in range(40): service.process_completed_bucket(a,p(i).time)
    live=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    assert live[-1]['trend_accel_3m']==pytest.approx(.05)
    assert live[-1]['trend_accel_5m']==pytest.approx(.05)
    assert live[0]['trend_accel_3m'] is None
    assert 'trend_accel_3m' not in json.loads(live[-1]['details'])
    service.rebuild(T,T+timedelta(seconds=800))
    assert live==analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')


def test_historical_null_runs_warmup_and_only_requested_window(analysis_repo):
    historical=datetime(2026,10,9,12,tzinfo=timezone.utc)
    # Shift the fixture to the actual historical date, without assigning runs.
    seed(analysis_repo)
    for i in range(40):
        analysis_repo._execute('UPDATE sensor_measurements SET time=%s WHERE time=%s',
                               ((historical+timedelta(seconds=20*i)).isoformat(),p(i).time.isoformat()),fetch=None)
    before=analysis_repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')
    assert all(row['run_id'] is None for row in before)
    service=AnalysisService(analysis_repo)
    start=historical+timedelta(seconds=601)
    end=historical+timedelta(seconds=799)
    assert service.rebuild(start,end)['points_written']==8
    rows=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    expected=ProcessAnalyzer()
    results=[expected.update(replace(p(i),time=historical+timedelta(seconds=20*i))) for i in range(39)]
    assert rows[0]['raw_mv_5m']==100 and rows[0]['trend_3m']==0
    assert rows[-1]['trend_accel_5m']==0
    assert json.loads(rows[-1]['details'])==asdict(results[-1].details)
    assert all(start <= datetime.fromisoformat(row['time']) < end for row in rows)
    assert analysis_repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')==before


def test_rebuild_replaces_stale_rows_and_preserves_other_ranges_and_versions(analysis_repo):
    seed(analysis_repo)
    service=AnalysisService(analysis_repo)
    service.rebuild(T,T+timedelta(seconds=800))
    analysis_repo.save_analysis([replace(ProcessAnalyzer().update(p(30)),algo_version='other-version')])
    # A stale row inside a now-incomplete final bucket must be removed as well.
    analysis_repo.save_analysis([ProcessAnalyzer().update(p(40))])
    analysis_repo._execute('UPDATE process_analysis SET raw_mv=-1 WHERE time=%s AND algo_version=%s',
                           (p(30).time.isoformat(),'cusum-v1'),fetch=None)
    before=analysis_repo._execute('SELECT * FROM process_analysis WHERE time < %s ORDER BY time', (p(30).time.isoformat(),))
    service.rebuild(p(30).time,p(40).time+timedelta(seconds=1))
    rows=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time,algo_version')
    assert len(rows)==41
    assert next(r for r in rows if r['time']==p(30).time.isoformat() and r['algo_version']=='cusum-v1')['raw_mv']==100
    assert any(r['algo_version']=='other-version' for r in rows)
    assert all(r['time']!=p(40).time.isoformat() for r in rows)
    assert analysis_repo._execute('SELECT * FROM process_analysis WHERE time < %s ORDER BY time', (p(30).time.isoformat(),))==before


def test_empty_rebuild_removes_stale_analysis(analysis_repo):
    analysis_repo.save_analysis([ProcessAnalyzer().update(p(0))])
    assert AnalysisService(analysis_repo).rebuild(T,p(1).time)['points_written']==0
    assert analysis_repo._execute('SELECT * FROM process_analysis')==[]


def test_replacement_rolls_back_on_insert_failure(analysis_repo):
    import sqlite3
    service=AnalysisService(analysis_repo)
    seed(analysis_repo)
    service.rebuild(T,p(40).time)
    before=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    good=ProcessAnalyzer().update(p(0))
    bad=replace(ProcessAnalyzer().update(p(1)),detector_score=None)
    with pytest.raises(sqlite3.IntegrityError):
        analysis_repo.save_analysis([good,bad],replace_range=(T,p(40).time,'cusum','cusum-v1'))
    assert analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')==before


def test_multiple_brands_live_replay_and_long_state_history(analysis_repo):
    from disti.hardware.base import SensorReading
    for sensor in ('vapor-temp','ec-1','ec-temp'):
        analysis_repo.ensure_sensor(sensor,sensor,'test')
    # >30 min history matters for the latched baseline, not just trend windows.
    points=[p(i,t=82 if i<60 else 85,mv=100 if i<60 else 112) for i in range(120)]
    points += [p(120,t=70),p(121,t=70)]
    # A gap and a cold interval separate the next heating process.
    points += [p(i,t=70 if i<130 else 82,mv=90) for i in range(125,180)]
    for point in points:
        for sensor,value,mv in [('vapor-temp',point.vapor_temp,None),('ec-1',1,point.raw_mv),('ec-temp',40,point.pt_raw_mv)]:
            analysis_repo.save_measurement(SensorReading(sensor,'temperature' if sensor!='ec-1' else 'conductivity',
                value,'test',timestamp=point.time,raw_mv=mv))
    service=AnalysisService(analysis_repo)
    analyzer=ProcessAnalyzer()
    live_results=[service.process_completed_bucket(analyzer,p(i).time) for i in range(180)]
    assert live_results[119].detector_alarm
    assert live_results[120].process_state==S.ENDE
    assert live_results[123].process_state==S.ENDE
    assert live_results[130].process_state==S.AUFHEIZEN
    assert live_results[130].details.baseline_mu is None
    assert live_results[179].details.baseline_mu==90
    live=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    assert service.rebuild(T,p(180).time)['points_written']==180
    assert analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')==live
    # Subrange starts >30 min into a hot brand: earlier frozen mu must survive.
    assert service.rebuild(p(105).time,p(120).time)['points_written']==15
    assert analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')==live


def test_live_rejects_open_buckets_and_config_mismatch(analysis_repo):
    service=AnalysisService(analysis_repo)
    with pytest.raises(ValueError,match='not complete'):
        service.process_completed_bucket(ProcessAnalyzer(),datetime(2099,1,1,tzinfo=timezone.utc))
    with pytest.raises(ValueError,match='config must match'):
        service.save_completed_point(ProcessAnalyzer(fast()),p(0))


def test_api_rejects_run_filter_and_naive_timestamps(analysis_repo):
    client=create_app(analysis_repo).test_client()
    base={'from':T.isoformat(),'to':p(40).time.isoformat()}
    assert client.post('/api/analysis/rebuild',json={**base,'run_id':'11111111-1111-1111-1111-111111111111'}).status_code==400
    assert client.post('/api/analysis/rebuild',json={**base,'from':'2026-01-01T00:00:00'}).status_code==400


def test_tail_config_and_derived_hysteresis():
    c=AnalysisConfig()
    assert c.cusum_h==8 and c.cusum_alarm_off==2.4
    assert replace(c,cusum_h=10).cusum_alarm_off==3
    assert (c.cusum_k,c.sigma_min_mv,c.cusum_leak,c.z_clip)==(.75,1.5,.995,None)


@pytest.mark.parametrize('s,score',[(0,0),(4,.5),(8,1),(12,1.5),(16,2),(24,2)])
@pytest.mark.parametrize('alarm',[False,True])
def test_detector_score_is_gradual_independent_of_alarm_and_persisted(analysis_repo,s,score,alarm):
    a=ProcessAnalyzer(fast())
    for i in range(5): a.update(p(i))
    # Below the existing detection gate, S and alarm are preserved. This lets
    # us verify all technical score levels independently of Boolean hysteresis.
    a.s,a.alarm=s,alarm
    result=AnalysisService(analysis_repo,a.config).save_completed_point(a,p(5,t=83))
    assert result.detector_score==score and result.detector_alarm==alarm
    row=analysis_repo._execute('SELECT * FROM process_analysis')[0]
    assert row['detector_score']==score and bool(row['detector_alarm'])==alarm
    assert json.loads(row['details'])['cusum_s']==s


def test_score_before_alarm_and_strict_hysteresis_boundaries():
    a=ProcessAnalyzer(fast(sigma_min_mv=2))
    for i in range(5): a.update(p(i))
    r=a.update(p(5,t=85,mv=100+2*(4+.75)))
    assert r.details.cusum_s==4 and r.detector_score==.5 and not r.detector_alarm
    # Choose z to reach the boundary exactly after the unchanged leak/k formula.
    r=a.update(p(6,t=85,mv=100+2*(8-.995*4+.75)))
    assert r.details.cusum_s==pytest.approx(8) and r.detector_score==pytest.approx(1)
    assert not r.detector_alarm
    r=a.update(p(7,t=85,mv=100+2*(10-.995*8+.75)))
    assert r.detector_alarm
    r=a.update(p(8,t=85,mv=100+2*(3-.995*10+.75)))
    assert r.details.cusum_s==pytest.approx(3)
    assert r.detector_alarm
    r=a.update(p(9,t=85,mv=100))
    assert r.details.cusum_s<2.4 and not r.detector_alarm


class ControlledHeadsFeatures:
    """Unit-test fixture: supply feature values without changing their formulas."""
    def __init__(self):
        from disti.process_analysis.models import Features
        self.value=Features(dtdt=0,trend_3m=-1,trend_5m=-1,trend_accel_3m=.1)
    def reset(self):
        pass
    def update(self,point):
        return self.value


def heads_analyzer():
    a=ProcessAnalyzer(fast())
    for i in range(4): a.update(p(i))
    features=ControlledHeadsFeatures()
    a.features=features
    return a,features


def head_point(a,features,i,trend=-.08,trend5=-.08,accel=.1,dtdt=0,**input_changes):
    features.value=replace(features.value,dtdt=dtdt,trend_3m=trend,trend_5m=trend5,trend_accel_3m=accel)
    return a.update(p(i,**input_changes))


def test_heads_plateau_gate_and_clear_negative_trend():
    a=ProcessAnalyzer(fast());f=ControlledHeadsFeatures();a.features=f
    for i in range(10):
        assert head_point(a,f,i,trend=0,accel=.1,dtdt=2).process_state==S.AUFHEIZEN
    assert a.plateau_time is None
    for i in range(10,13): head_point(a,f,i,trend=-1)
    assert a.plateau_time==p(12).time
    for i in range(13,25):
        assert head_point(a,f,i,trend=-1).process_state==S.VORLAUF


def test_heads_two_stage_persistence_and_middle_latch():
    a,f=heads_analyzer()
    for i in range(4,7):
        assert head_point(a,f,i).process_state==S.VORLAUF
    assert head_point(a,f,7).process_state==S.VORLAUF_AUSKLANG
    for i in range(8,14):
        assert head_point(a,f,i,trend=0,trend5=0,accel=0).process_state==S.VORLAUF_AUSKLANG
    assert head_point(a,f,14,trend=0,trend5=0,accel=0).process_state==S.MITTELLAUF
    # A later negative trend or loss of plateau must not revoke MITTELLAUF.
    assert head_point(a,f,15,trend=-1,trend5=-1,accel=-.1,dtdt=2).process_state==S.MITTELLAUF
    assert head_point(a,f,16,t=70).process_state==S.ENDE
    assert head_point(a,f,17).process_state==S.AUFHEIZEN
    assert a.heads_state==S.VORLAUF and a.heads_middle_since is None


def test_short_acceleration_spike_and_strict_exit_thresholds():
    a,f=heads_analyzer()
    assert head_point(a,f,4).process_state==S.VORLAUF
    assert head_point(a,f,5).process_state==S.VORLAUF
    assert head_point(a,f,6,accel=0).process_state==S.VORLAUF
    assert a.heads_exit_since is None
    for i in range(7,12):
        assert head_point(a,f,i,trend=-.10).process_state==S.VORLAUF
    for i in range(12,15):
        assert head_point(a,f,i).process_state==S.VORLAUF
    assert head_point(a,f,15).process_state==S.VORLAUF_AUSKLANG


def test_heads_exit_falls_back_and_restarts_persistence():
    a,f=heads_analyzer()
    for i in range(4,8): head_point(a,f,i)
    assert head_point(a,f,8,trend=0,trend5=0).process_state==S.VORLAUF_AUSKLANG
    assert head_point(a,f,9,trend=-.2).process_state==S.VORLAUF
    assert a.heads_middle_since is None
    for i in range(10,13):
        assert head_point(a,f,i).process_state==S.VORLAUF
    assert head_point(a,f,13).process_state==S.VORLAUF_AUSKLANG


@pytest.mark.parametrize('interruption',['missing','invalid','gap','plateau'])
def test_heads_exit_persistence_is_interrupted(interruption):
    a,f=heads_analyzer()
    head_point(a,f,4);head_point(a,f,5)
    if interruption=='missing': head_point(a,f,6,mv=None)
    elif interruption=='invalid': head_point(a,f,6,invalid=True)
    elif interruption=='gap': head_point(a,f,7)
    else: head_point(a,f,6,dtdt=2)
    start=8 if interruption=='gap' else 7
    for i in range(start,start+3):
        assert head_point(a,f,i).process_state==S.VORLAUF
    assert head_point(a,f,start+3).process_state==S.VORLAUF_AUSKLANG


@pytest.mark.parametrize('interruption',['missing','invalid','gap','plateau','trend3','trend5','unknown'])
def test_middle_needs_both_trends_plateau_and_unbroken_persistence(interruption):
    a,f=heads_analyzer()
    for i in range(4,8): head_point(a,f,i)
    for i in range(8,11): head_point(a,f,i,trend=0,trend5=0)
    changes={'trend':0,'trend5':0}
    if interruption=='missing': changes['mv']=None
    elif interruption=='invalid': changes['invalid']=True
    elif interruption=='plateau': changes['dtdt']=2
    elif interruption=='trend3': changes['trend']=-.08
    elif interruption=='trend5': changes['trend5']=-.08
    elif interruption=='unknown': changes['trend5']=None
    index=12 if interruption=='gap' else 11
    head_point(a,f,index,**changes)
    for i in range(index+1,index+7):
        assert head_point(a,f,i,trend=-.05,trend5=-.05).process_state==S.VORLAUF_AUSKLANG
    assert head_point(a,f,index+7,trend=-.05,trend5=-.05).process_state==S.MITTELLAUF


def test_middle_is_overridden_by_tail_and_end_and_reset_clears_heads():
    a,f=heads_analyzer()
    for i in range(4,8): head_point(a,f,i)
    for i in range(8,15): head_point(a,f,i,trend=0,trend5=0)
    assert a.heads_state==S.MITTELLAUF
    assert head_point(a,f,15,t=85,mv=130).process_state==S.NACHLAUF_ENTWICKELT
    assert head_point(a,f,16,t=86,mv=130).process_state==S.NACHLAUF_WAHRSCHEINLICH
    assert head_point(a,f,17,t=70).process_state==S.ENDE
    a.reset()
    assert a.heads_state==S.VORLAUF and a.heads_exit_since is None and a.heads_middle_since is None


def test_heads_actual_features_live_and_rebuild_identical(analysis_repo):
    from disti.hardware.base import SensorReading
    for sensor in ('vapor-temp','ec-1','ec-temp'):
        analysis_repo.ensure_sensor(sensor,sensor,'test')
    for i in range(150):
        mv=100+20*math.exp(-(i/3)/3)
        for sensor,value,raw in [('vapor-temp',82,None),('ec-1',1,mv),('ec-temp',40,1000)]:
            analysis_repo.save_measurement(SensorReading(sensor,'temperature' if sensor!='ec-1' else 'conductivity',
                value,'test',timestamp=p(i).time,raw_mv=raw))
    before=analysis_repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')
    service=AnalysisService(analysis_repo);a=ProcessAnalyzer()
    live=[service.process_completed_bucket(a,p(i).time) for i in range(150)]
    transitions=[r.process_state for i,r in enumerate(live) if i==0 or r.process_state!=live[i-1].process_state]
    assert transitions==[S.AUFHEIZEN,S.VORLAUF,S.VORLAUF_AUSKLANG,S.MITTELLAUF]
    rows=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')
    assert service.rebuild(T,p(150).time)['points_written']==150
    assert analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')==rows
    assert service.rebuild(p(100).time,p(150).time)['points_written']==50
    assert analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time')==rows
    assert analysis_repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')==before


def test_alarm_off_boundary_is_strict_with_exactly_representable_values():
    # h=10 gives alarm_off=3, so the strict equality check avoids rounding at
    # the default decimal 2.4. The default values are covered above.
    a=ProcessAnalyzer(fast(cusum_h=10,cusum_leak=1,sigma_min_mv=2))
    for i in range(5): a.update(p(i))
    a.s,a.alarm=4,True
    r=a.update(p(5,t=85,mv=99.5))
    assert r.details.cusum_s==a.config.cusum_alarm_off==3 and r.detector_alarm
    assert not a.update(p(6,t=85,mv=100)).detector_alarm
