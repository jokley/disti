from datetime import timedelta
import logging

import pytest

from disti.process_analysis import AnalysisConfig
from disti.process_analysis.service import AnalysisService
from disti.process_analysis.worker import AnalysisWorker
from disti.hardware.base import SensorReading
from test_process_analysis import T, p, seed, analysis_repo


def worker(repo, seconds):
    return AnalysisWorker(repo, clock=lambda: T+timedelta(seconds=seconds))


def rows(repo):
    return repo._execute('SELECT * FROM process_analysis ORDER BY time')


def test_new_complete_buckets_and_open_bucket_excluded(analysis_repo):
    seed(analysis_repo)
    w=worker(analysis_repo,39)
    assert w.tick()==1 and len(rows(analysis_repo))==1
    assert w.analyzer.last_time==T
    assert w.tick()==0
    w.clock=lambda: T+timedelta(seconds=40)
    assert w.tick()==1 and len(rows(analysis_repo))==2
    w.clock=lambda: T+timedelta(seconds=61)
    assert w.tick()==1
    assert rows(analysis_repo)[-1]['time']==p(2).time.isoformat()


def test_restart_only_writes_missing_tail_and_restores_all_features(analysis_repo,monkeypatch):
    seed(analysis_repo)
    service=AnalysisService(analysis_repo)
    service.rebuild(T,p(20).time)
    prefix=rows(analysis_repo)
    original_save=analysis_repo.save_analysis
    writes=[]
    def save(results,**kwargs):
        writes.extend(r.time for r in results)
        return original_save(results,**kwargs)
    monkeypatch.setattr(analysis_repo,'save_analysis',save)
    w=worker(analysis_repo,800)
    assert w.tick()==20
    assert writes==[p(i).time for i in range(20,40)]
    assert rows(analysis_repo)[:20]==prefix
    live=rows(analysis_repo)
    monkeypatch.setattr(analysis_repo,'save_analysis',original_save)
    service.rebuild(T,p(40).time)
    assert rows(analysis_repo)==live
    restarted=worker(analysis_repo,800)
    assert restarted.tick()==0
    assert restarted.analyzer.last_time==w.analyzer.last_time
    assert restarted.analyzer.mu==w.analyzer.mu
    assert restarted.analyzer.s==w.analyzer.s
    assert restarted.analyzer.features.trend_history==w.analyzer.features.trend_history


def test_start_without_data_then_arriving_measurements_are_automatic(analysis_repo):
    w=worker(analysis_repo,800)
    assert w.tick()==0 and w.analyzer is None
    seed(analysis_repo)
    assert w.tick()==40
    assert len(rows(analysis_repo))==40
    assert w.tick()==0
    assert worker(analysis_repo,800).tick()==0


def test_existing_upsert_keeps_reprocessing_idempotent(analysis_repo):
    seed(analysis_repo)
    assert worker(analysis_repo,800).tick()==40
    expected=rows(analysis_repo)
    # An uncertain save acknowledgement can logically retry a bucket with a
    # separately restored analyzer; the existing PK/upsert prevents duplicates.
    from disti.process_analysis import ProcessAnalyzer
    a=ProcessAnalyzer();service=AnalysisService(analysis_repo)
    for i in range(40): service.process_completed_bucket(a,p(i).time)
    assert rows(analysis_repo)==expected


@pytest.mark.parametrize('committed',[False,True])
def test_failed_save_restores_mutated_analyzer_before_retry(analysis_repo,monkeypatch,committed):
    seed(analysis_repo)
    w=worker(analysis_repo,800)
    real_save=analysis_repo.save_analysis
    failed=False
    def fail_once(results,**kwargs):
        nonlocal failed
        if results[0].time==p(10).time and not failed:
            failed=True
            if committed: real_save(results,**kwargs)
            raise RuntimeError('temporary write failure')
        return real_save(results,**kwargs)
    monkeypatch.setattr(analysis_repo,'save_analysis',fail_once)
    with pytest.raises(RuntimeError): w.tick()
    assert w.analyzer is None and w.next_bucket is None
    assert len(rows(analysis_repo))==(11 if committed else 10)
    assert w.tick()==(29 if committed else 30)
    live=rows(analysis_repo)
    AnalysisService(analysis_repo).rebuild(T,p(40).time)
    assert rows(analysis_repo)==live


def test_loop_logs_temporary_db_error_waits_then_retries(analysis_repo,monkeypatch,caplog):
    seed(analysis_repo)
    w=worker(analysis_repo,800)
    original=analysis_repo.latest_analysis_time
    failed=False
    def unavailable(*args):
        nonlocal failed
        if not failed:
            failed=True
            raise RuntimeError('temporary database outage')
        return original(*args)
    monkeypatch.setattr(analysis_repo,'latest_analysis_time',unavailable)
    class Stop:
        waits=[]
        def is_set(self): return len(self.waits)==2
        def wait(self,seconds): self.waits.append(seconds)
    stop=Stop()
    with caplog.at_level(logging.ERROR): w.run(stop)
    assert 'retrying' in caplog.text
    assert stop.waits==[2,2]
    assert len(rows(analysis_repo))==40


def test_restart_preserves_long_frozen_baseline_cusum_and_temperature_stages(analysis_repo):
    for sensor in ('vapor-temp','ec-1','ec-temp'): analysis_repo.ensure_sensor(sensor,sensor,'test')
    for i in range(180):
        temp=76+i*.5 if i<6 else 78.5 if i<100 else 85
        mv=100 if i<100 else 112
        for sensor,value,raw in [('vapor-temp',temp,None),('ec-1',1,mv),('ec-temp',40,1000)]:
            analysis_repo.save_measurement(SensorReading(sensor,'temperature' if sensor!='ec-1' else 'conductivity',value,'test',timestamp=p(i).time,raw_mv=raw))
    w=worker(analysis_repo,3000)
    assert w.tick()==150
    frozen=w.analyzer.mu
    resumed=worker(analysis_repo,3600)
    assert resumed.tick()==30 and resumed.analyzer.mu==frozen
    assert resumed.analyzer.baseline_frozen and resumed.analyzer.alarm
    live=rows(analysis_repo)
    assert {r['process_state'] for r in live} >= {'AUFHEIZEN','VORLAUF','VORLAUF_AUSKLANG','MITTELLAUF','NACHLAUF_ENTWICKELT'}
    AnalysisService(analysis_repo).rebuild(T,p(180).time)
    assert rows(analysis_repo)==live
    assert resumed.analyzer.config.cusum_h==8


def test_restart_fills_empty_buckets_and_respects_detector_version(analysis_repo):
    seed(analysis_repo)
    other=AnalysisService(analysis_repo,AnalysisConfig(algo_version='other'))
    other.rebuild(T,p(40).time)
    assert worker(analysis_repo,800).tick()==40
    w=worker(analysis_repo,860)
    assert w.tick()==3
    current=[r for r in rows(analysis_repo) if r['algo_version']=='cusum-v1']
    assert len(current)==43
    assert all(r['process_state']=='DATENLUECKE' for r in current[-3:])


def test_next_cycle_reads_only_new_bucket(analysis_repo,monkeypatch):
    seed(analysis_repo)
    w=worker(analysis_repo,800);w.tick()
    original=analysis_repo.analysis_buckets;queries=[]
    def query(*args,**kwargs):
        queries.append(kwargs.get('start'))
        return original(*args,**kwargs)
    monkeypatch.setattr(analysis_repo,'analysis_buckets',query)
    w.clock=lambda: T+timedelta(seconds=840)
    assert w.tick()==2
    assert queries==[p(40).time,p(41).time]


def test_running_loop_publishes_new_buckets_without_manual_rebuild(analysis_repo):
    w=worker(analysis_repo,0)
    class Stop:
        cycles=0
        def is_set(self): return self.cycles==3
        def wait(self,seconds):
            assert seconds==2
            self.cycles+=1
            if self.cycles==1:
                seed(analysis_repo)
                w.clock=lambda: T+timedelta(seconds=20)
            else:
                w.clock=lambda: T+timedelta(seconds=40)
    w.run(Stop())
    assert len(rows(analysis_repo))==2
    assert rows(analysis_repo)[-1]['time']==p(1).time.isoformat()


def test_sensor_quality_error_is_analyzed_without_stopping_worker(analysis_repo):
    seed(analysis_repo)
    analysis_repo._execute("UPDATE sensor_measurements SET quality='error' WHERE time=%s AND sensor_id='ec-1'",
                           (p(5).time.isoformat(),),fetch=None)
    w=worker(analysis_repo,800)
    assert w.tick()==40
    assert rows(analysis_repo)[5]['process_state']=='SENSOR_UNGUELTIG'
    assert rows(analysis_repo)[6]['process_state']!='SENSOR_UNGUELTIG'
    assert w.tick()==0
