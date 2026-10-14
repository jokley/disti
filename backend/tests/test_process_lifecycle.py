from datetime import timedelta
from pathlib import Path

import pytest

from disti.process_analysis import AnalysisConfig,ProcessAnalyzer,ProcessState as S
from test_process_analysis import T,p,fast,ControlledTemperatureFeatures,slope_point,analysis_repo,seed


def lifecycle(config=None,phase=S.BEREIT):
    a=ProcessAnalyzer(config or AnalysisConfig())
    a.process_state=phase
    f=ControlledTemperatureFeatures();a.features=f
    return a,f


def test_operating_states_and_quality_overlays():
    assert {s.value for s in S}=={'BEREIT','AUFHEIZEN','VORLAUF','VORLAUF_AUSKLANG','MITTELLAUF',
        'NACHLAUF_ENTWICKELT','NACHLAUF','ABKÜHLEN','DATENLUECKE','SENSOR_UNGUELTIG'}


def test_quiet_plant_is_ready_and_brief_positive_spike_is_ignored():
    a,f=lifecycle()
    for i in range(15): assert slope_point(a,f,i,0,t=35).process_state==S.BEREIT
    assert slope_point(a,f,15,.8,t=35).process_state==S.BEREIT
    assert slope_point(a,f,16,0,t=35).process_state==S.BEREIT
    for i in range(17,22): assert slope_point(a,f,i,.20,t=35).process_state==S.BEREIT


@pytest.mark.parametrize('base',[20,55,80])
def test_real_slow_rise_starts_before_strong_heating_without_absolute_gate(base):
    a=ProcessAnalyzer()
    results=[a.update(p(i,t=base+.1*i)) for i in range(10)]
    assert results[0].process_state==S.BEREIT
    assert results[3].process_state==S.BEREIT
    assert results[4].process_state==S.AUFHEIZEN
    assert results[4].features.dtdt==pytest.approx(.3)
    assert not a.heating_seen # below the unchanged 1.0 strong-heat threshold


def test_original_heads_windows_and_confirmation_are_retained():
    a,f=lifecycle(fast())
    states=[]
    for i in range(14): states.append(slope_point(a,f,i,2 if i<4 else 0).process_state)
    assert states[:3]==[S.BEREIT]*3
    assert states[3:6]==[S.AUFHEIZEN]*3
    assert states[6:8]==[S.VORLAUF]*2
    assert states[8:13]==[S.VORLAUF_AUSKLANG]*5
    assert states[13]==S.MITTELLAUF
    assert slope_point(a,f,14,0,t=85,mv=130).process_state==S.NACHLAUF_ENTWICKELT
    assert slope_point(a,f,15,0,t=86,mv=130).process_state==S.NACHLAUF


def test_tail_only_renamed_and_cusum_math_is_unchanged():
    a,f=lifecycle(fast())
    for i in range(5): slope_point(a,f,i,0)
    r=slope_point(a,f,5,0,t=86,mv=130)
    assert r.process_state==S.NACHLAUF and r.detector_alarm
    assert r.details.cusum_s==pytest.approx(r.details.z-.75)
    assert r.detector_score==min(r.details.cusum_s/8,2)
    previous=r.details.cusum_s
    r=slope_point(a,f,6,0,t=86,mv=110)
    assert r.details.cusum_s==pytest.approx(max(0,.995*previous+r.details.z-.75))
    assert a.config.cusum_h==8 and a.config.cusum_alarm_off==2.4


def test_one_negative_spike_cannot_start_cooling_even_after_detector_stop():
    a,f=lifecycle(phase=S.NACHLAUF)
    slope_point(a,f,0,0,t=90)
    assert slope_point(a,f,1,-3,t=87).process_state==S.NACHLAUF
    assert a.ended # old detector end rule remains intact, but is not a UI state
    for i in range(2,7): assert slope_point(a,f,i,0,t=87).process_state==S.NACHLAUF


def test_cooling_needs_both_persistent_negative_gradient_and_relative_drop():
    a,f=lifecycle(phase=S.NACHLAUF)
    slope_point(a,f,0,0,t=90)
    for i in range(1,6):
        assert slope_point(a,f,i,-.6,t=90-.1*i).process_state==S.NACHLAUF
    assert slope_point(a,f,6,-.6,t=87.9).process_state==S.ABKUEHLEN
    b,g=lifecycle(phase=S.NACHLAUF)
    slope_point(b,g,0,0,t=90)
    for i in range(1,4): assert slope_point(b,g,i,-.6,t=90-.6*i).process_state==S.NACHLAUF
    assert slope_point(b,g,4,-.6,t=87.6).process_state==S.ABKUEHLEN


def test_cooling_requires_recent_peak_not_old_process_maximum():
    a,f=lifecycle(phase=S.NACHLAUF)
    slope_point(a,f,0,0,t=90)
    for i in range(1,19): slope_point(a,f,i,0,t=89)
    # Peak 90 is outside the 300 s window; current fall from 89 is <2.
    for i in range(19,24):
        assert slope_point(a,f,i,-.6,t=87.5).process_state==S.NACHLAUF


@pytest.mark.parametrize('temperature',[20,55,82])
def test_cooling_becomes_ready_from_quiet_dynamics_at_any_temperature(temperature):
    a,f=lifecycle(phase=S.ABKUEHLEN)
    for i in range(9):
        assert slope_point(a,f,i,0,t=temperature).process_state==S.ABKUEHLEN
    assert slope_point(a,f,9,0,t=temperature).process_state==S.BEREIT
    for i in range(10,13): assert slope_point(a,f,i,.3,t=temperature).process_state==S.BEREIT
    assert slope_point(a,f,13,.3,t=temperature).process_state==S.AUFHEIZEN


def test_ready_window_is_robust_but_does_not_accept_continuing_movement():
    a,f=lifecycle(phase=S.ABKUEHLEN)
    for i in range(15): assert slope_point(a,f,i,-.15,t=40).process_state==S.ABKUEHLEN
    for i in range(15,23): slope_point(a,f,i,0,t=40)
    assert slope_point(a,f,23,.4,t=40).process_state==S.BEREIT # 8/9 stable, median zero


@pytest.mark.parametrize('kind',['missing','invalid','gap'])
def test_lifecycle_persistence_cannot_bridge_data_errors(kind):
    a,f=lifecycle()
    slope_point(a,f,0,.4,t=30);slope_point(a,f,1,.4,t=30)
    if kind=='missing': slope_point(a,f,2,.4,t=30,mv=None)
    elif kind=='invalid': slope_point(a,f,2,.4,t=30,invalid=True)
    else: slope_point(a,f,3,.4,t=30)
    start=4 if kind=='gap' else 3
    for i in range(start,start+3): assert slope_point(a,f,i,.4,t=30).process_state==S.BEREIT
    assert slope_point(a,f,start+3,.4,t=30).process_state==S.AUFHEIZEN


def test_cooling_quiet_window_restarts_after_missing_data():
    a,f=lifecycle(phase=S.ABKUEHLEN)
    for i in range(8): slope_point(a,f,i,0,t=40)
    assert slope_point(a,f,8,0,t=40,mv=None).process_state==S.DATENLUECKE
    for i in range(9,18): assert slope_point(a,f,i,0,t=40).process_state==S.ABKUEHLEN
    assert slope_point(a,f,18,0,t=40).process_state==S.BEREIT


def test_migration_invalidates_only_legacy_cache_series_and_is_repeatable(analysis_repo):
    from dataclasses import replace
    from disti.process_analysis.service import AnalysisService
    seed(analysis_repo)
    service=AnalysisService(analysis_repo);service.rebuild(T,p(40).time)
    first=ProcessAnalyzer().update(p(0))
    analysis_repo.save_analysis([replace(first,algo_version='unaffected')])
    raw=analysis_repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')
    analysis_repo._execute("UPDATE process_analysis SET process_state='ENDE' WHERE time=%s AND algo_version='cusum-v1'",(p(10).time.isoformat(),),fetch=None)
    sql=(Path(__file__).parents[1]/'migrations/006_operating_process_states.sql').read_text()
    def migrate():
        conn=analysis_repo.connection_factory()
        try: conn.executescript(sql)
        finally: conn.close()
    migrate()
    assert {r['algo_version'] for r in analysis_repo._execute('SELECT * FROM process_analysis')}=={'unaffected'}
    # Unchanged live bootstrap can now reproduce the entire affected series.
    from disti.process_analysis.worker import AnalysisWorker
    assert AnalysisWorker(analysis_repo,clock=lambda:p(40).time).tick()==40
    rebuilt=analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time,algo_version')
    migrate()
    assert analysis_repo._execute('SELECT * FROM process_analysis ORDER BY time,algo_version')==rebuilt
    assert analysis_repo._execute('SELECT * FROM sensor_measurements ORDER BY time,id')==raw


def test_current_state_panel_reads_latest_string_outside_dashboard_window(analysis_repo):
    import json
    from disti.process_analysis.service import AnalysisService
    seed(analysis_repo);AnalysisService(analysis_repo).rebuild(T,p(40).time)
    d=json.loads((Path(__file__).parents[2]/'grafana/dashboards/Distillation.json').read_text())
    panel=next(p for p in d['panels'] if p['id']==25)
    query=panel['targets'][0]['rawSql'].replace('${analysis_detector:sqlstring}','%s').replace('${analysis_version:sqlstring}','%s')
    assert '$__timeFilter' not in query
    row=analysis_repo._execute(query,('cusum','cusum-v1'),'one')
    assert row['Prozessstatus']=='BEREIT' and isinstance(row['Prozessstatus'],str)
    assert panel['options']['reduceOptions']['fields']=='Prozessstatus'
    assert panel['options']['reduceOptions']['values'] is True
    assert all(v['hide']==2 for v in d['templating']['list'] if v['name'] in ('analysis_detector','analysis_version'))
