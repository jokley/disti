import json
from pathlib import Path

DASHBOARD_PATH = Path(__file__).parents[2] / 'grafana/dashboards/Distillation.json'

def dashboard():
    return json.loads(DASHBOARD_PATH.read_text())

def test_persisted_analysis_panels():
    panels = dashboard()['panels']
    analysis = [p for p in panels if 20 <= p['id'] <= 25]
    assert len(analysis) == 6
    assert next(p for p in analysis if p['title']=='Prozessstatus')['type']=='state-timeline'
    assert next(p for p in analysis if p['id']==25)['type']=='stat'
    for p in analysis:
        sql=p['targets'][0]['rawSql']
        assert 'FROM process_analysis' in sql
        assert '$__timeFilter(time)' in sql
        assert 'analysis_version' in sql and 'analysis_detector' in sql
        assert 'run_id' not in sql and 'analysis_run' not in sql
        assert not any(s in sql.lower() for s in ('sensor_measurements','lag(', 'avg(', 'with ', 'insert ', 'update ', 'delete '))
    assert 'ORDER BY time DESC LIMIT 1' in analysis[-1]['targets'][0]['rawSql']

def test_detector_diagnostics_and_units():
    panels={p['id']:p for p in dashboard()['panels']}
    assert "details->>'baseline_mu'" in panels[20]['targets'][0]['rawSql']
    assert '50 * detector_score' in panels[21]['targets'][0]['rawSql']
    assert 'keine statistische Wahrscheinlichkeit' in panels[21]['description']
    steps=panels[21]['fieldConfig']['overrides'][0]['properties'][1]['value']['steps']
    assert [s['value'] for s in steps]==[None,4,8]
    assert panels[23]['fieldConfig']['overrides'][0]['properties'][1]['value']=='right'


def test_comparison_panel_reads_persisted_trend_dynamics():
    panel=next(p for p in dashboard()['panels'] if p['title']=='Vergleichsmarker')
    sql=panel['targets'][0]['rawSql']
    for field in ('trend_1m','trend_3m','trend_5m','trend_accel_3m','trend_accel_5m','rise_from_min_5m'):
        assert field in sql
    assert 'cusum_s' not in sql and 'lag(' not in sql.lower()
    accel=next(o for o in panel['fieldConfig']['overrides'] if o['matcher']['options']=='Trendänderung.*')
    assert {'id':'unit','value':'suffix:mV/min²'} in accel['properties']


def test_analysis_has_no_run_selector():
    assert 'analysis_run' not in {v['name'] for v in dashboard()['templating']['list']}


def test_gradual_score_display_and_process_state_mappings():
    panels={p['id']:p for p in dashboard()['panels']}
    for panel_id in (21,25):
        panel=panels[panel_id]
        assert '50 * detector_score' in panel['targets'][0]['rawSql']
        assert 'detector_score * 100' not in panel['targets'][0]['rawSql']
        score=next(o for o in panel['fieldConfig']['overrides'] if o['matcher']['options']=='Nachlauf-Score')
        props={p['id']:p['value'] for p in score['properties']}
        assert props['min']==0 and props['max']==100
        assert props['thresholds']['steps'][-1]['value']==50
        assert 'keine statistische Wahrscheinlichkeit' in panel['description']
    mappings=panels[24]['fieldConfig']['defaults']['mappings'][0]['options']
    for state in ('VORLAUF','VORLAUF_AUSKLANG','MITTELLAUF','NACHLAUF_ENTWICKELT','NACHLAUF_WAHRSCHEINLICH'):
        assert mappings[state]['text']==state


def test_temperature_and_ec_diagnostics_use_persisted_fields():
    panel=next(p for p in dashboard()['panels'] if p['id']==22)
    sql=panel['targets'][0]['rawSql']
    for field in ('ec_plateau_ref','ec_drop_from_plateau','ec_min_since_plateau','ec_recovery_from_min','trend_1m','trend_3m','dtdt','vapor_temp','raw_mv'):
        assert field in sql
    assert ' - ' not in sql and 'lag(' not in sql.lower()
    for name in ('EC-Abfall vom Plateau (mV)','EC-Erholung vom Minimum (mV)'):
        override=next(o for o in panel['fieldConfig']['overrides'] if o['matcher']['options']==name)
        assert all(p['id']!='thresholds' for p in override['properties'])
    assert 'EC, Trends und Recovery sind nur diagnostisch' in panel['description']
    assert '120-s-Fenster' in panel['description']
