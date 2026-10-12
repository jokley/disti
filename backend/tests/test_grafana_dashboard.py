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
        assert 'analysis_version' in sql and 'analysis_run' in sql
        assert not any(s in sql.lower() for s in ('sensor_measurements','lag(', 'avg(', 'with ', 'insert ', 'update ', 'delete '))
    assert 'ORDER BY time DESC LIMIT 1' in analysis[-1]['targets'][0]['rawSql']

def test_detector_diagnostics_and_units():
    panels={p['id']:p for p in dashboard()['panels']}
    assert "details->>'baseline_mu'" in panels[20]['targets'][0]['rawSql']
    assert 'LEAST(detector_score * 100, 100)' in panels[21]['targets'][0]['rawSql']
    assert 'keine statistische Wahrscheinlichkeit' in panels[21]['description']
    steps=panels[21]['fieldConfig']['overrides'][0]['properties'][1]['value']['steps']
    assert [s['value'] for s in steps]==[None,3,6]
    assert panels[23]['fieldConfig']['overrides'][0]['properties'][1]['value']=='right'


def test_comparison_panel_reads_persisted_trend_dynamics():
    panel=next(p for p in dashboard()['panels'] if p['title']=='Vergleichsmarker')
    sql=panel['targets'][0]['rawSql']
    for field in ('trend_1m','trend_3m','trend_5m','trend_accel_3m','trend_accel_5m','rise_from_min_5m'):
        assert field in sql
    assert 'cusum_s' not in sql and 'lag(' not in sql.lower()
    accel=next(o for o in panel['fieldConfig']['overrides'] if o['matcher']['options']=='Trendänderung.*')
    assert {'id':'unit','value':'suffix:mV/min²'} in accel['properties']
