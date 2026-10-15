import json
from pathlib import Path

DASHBOARD_PATH = Path(__file__).parents[2] / 'grafana/dashboards/Distillation.json'

def dashboard():
    return json.loads(DASHBOARD_PATH.read_text())


def all_panels():
    def flatten(panels):
        for panel in panels:
            yield panel
            yield from flatten(panel.get('panels',[]))
    return list(flatten(dashboard()['panels']))

def test_persisted_analysis_panels():
    panels = all_panels()
    analysis = [p for p in panels if 20 <= p['id'] <= 29]
    assert len(analysis) == 10
    assert next(p for p in analysis if p['title']=='Prozessstatus')['type']=='state-timeline'
    assert next(p for p in analysis if p['id']==25)['type']=='stat'
    for p in analysis:
        sql=p['targets'][0]['rawSql']
        assert 'FROM process_analysis' in sql
        assert ('$__timeFilter(time)' in sql) == (p['id']!=25)
        assert 'analysis_version' in sql and 'analysis_detector' in sql
        assert 'run_id' not in sql and 'analysis_run' not in sql
        assert not any(s in sql.lower() for s in ('sensor_measurements','lag(', 'avg(', 'with ', 'insert ', 'update ', 'delete '))
    assert all('ORDER BY time DESC LIMIT 1' in p['targets'][0]['rawSql'] for p in analysis if p['id'] in (25,26))

def test_detector_diagnostics_and_units():
    panels={p['id']:p for p in all_panels()}
    assert "details->>'baseline_mu'" in panels[27]['targets'][0]['rawSql']
    assert '50 * detector_score' in panels[21]['targets'][0]['rawSql']
    assert 'keine statistische Wahrscheinlichkeit' in panels[21]['description']
    steps=panels[28]['fieldConfig']['overrides'][0]['properties'][1]['value']['steps']
    assert [s['value'] for s in steps]==[None,4,8]
    assert panels[23]['fieldConfig']['overrides'][0]['properties'][1]['value']=='right'


def test_comparison_panel_reads_persisted_trend_dynamics():
    panel=next(p for p in all_panels() if p['title']=='Vergleichsmarker')
    sql=panel['targets'][0]['rawSql']
    for field in ('trend_1m','trend_3m','trend_5m','trend_accel_3m','trend_accel_5m','rise_from_min_5m'):
        assert field in sql
    assert 'cusum_s' not in sql and 'lag(' not in sql.lower()
    accel=next(o for o in panel['fieldConfig']['overrides'] if o['matcher']['options']=='Trendänderung.*')
    assert {'id':'unit','value':'suffix:mV/min²'} in accel['properties']


def test_analysis_has_no_run_selector():
    assert 'analysis_run' not in {v['name'] for v in dashboard()['templating']['list']}


def test_gradual_score_display_and_process_state_mappings():
    panels={p['id']:p for p in all_panels()}
    for panel_id in (21,26):
        panel=panels[panel_id]
        assert '50 * detector_score' in panel['targets'][0]['rawSql']
        assert 'detector_score * 100' not in panel['targets'][0]['rawSql']
        score=next(o for o in panel['fieldConfig']['overrides'] if o['matcher']['options']=='Nachlauf-Score')
        props={p['id']:p['value'] for p in score['properties']}
        assert props['min']==0 and props['max']==100
        assert props['thresholds']['steps'][-1]['value']==50
        assert 'keine statistische Wahrscheinlichkeit' in panel['description']
    mappings=panels[24]['fieldConfig']['defaults']['mappings'][0]['options']
    for state in ('INAKTIV','AUFHEIZEN','INAKTIV','VORLAUF','VORLAUF_AUSKLANG','MITTELLAUF','NACHLAUF_ENTWICKELT','NACHLAUF'):
        assert mappings[state]['text']==state


def test_temperature_and_ec_diagnostics_use_persisted_fields():
    panel=next(p for p in all_panels() if p['id']==22)
    sql=panel['targets'][0]['rawSql']
    for field in ('ec_plateau_ref','ec_drop_from_plateau','ec_min_since_plateau','ec_recovery_from_min','trend_1m','trend_3m','dtdt','vapor_temp','raw_mv'):
        assert field in sql
    assert ' - ' not in sql and 'lag(' not in sql.lower()
    for name in ('EC-Abfall vom Plateau (mV)','EC-Erholung vom Minimum (mV)'):
        override=next(o for o in panel['fieldConfig']['overrides'] if o['matcher']['options']==name)
        assert all(p['id']!='thresholds' for p in override['properties'])
    assert 'EC, Trends und Recovery sind nur diagnostisch' in panel['description']
    assert '120-s-Fenster' in panel['description']


def test_operating_dashboard_is_led_by_temperatures_state_and_process_curve():
    main=dashboard()['panels']
    assert [p['title'] for p in main[:3]]==['Kesseldampf','Kühler','Aktueller Prozessstatus']
    assert all(p['type']=='stat' and p['gridPos']['y']==0 and p['gridPos']['h']==4 for p in main[:3])
    assert main[0]['fieldConfig']['defaults']['unit']=='celsius'
    assert main[0]['options']['text']['valueSize'] == main[1]['options']['text']['valueSize']
    assert main[2]['fieldConfig']['defaults']['mappings']==main[3]['fieldConfig']['defaults']['mappings']
    assert main[3]['type']=='state-timeline' and main[3]['gridPos']['w']==24
    sql=main[2]['targets'][0]['rawSql']
    assert 'process_state' in sql and 'detector_score' not in sql
    assert 'ORDER BY time DESC LIMIT 1' in sql
    curve=main[4]
    assert curve['title']=='Kesseldampf – Prozessverlauf' and curve['gridPos']['w']==24
    assert all(curve['gridPos']['h'] > p['gridPos']['h'] for p in main if p['type'] not in ('row',) and p['id']!=curve['id'])
    assert 'vapor_temp' in curve['targets'][0]['rawSql'] and 'dtdt' in curve['targets'][0]['rawSql']
    dynamics=next(p for p in main if p['title']=='Prozessdynamik')
    assert 'dtdt' in dynamics['targets'][0]['rawSql'] and '50 * detector_score' in dynamics['targets'][0]['rawSql']
    for name,expected in [('dT/dt (°C/min)',[None,0,.12,.20,.30]),('Nachlauf-Score',[None,50])]:
        override=next(o for o in dynamics['fieldConfig']['overrides'] if o['matcher']['options']==name)
        props={p['id']:p['value'] for p in override['properties']}
        assert [s['value'] for s in props['thresholds']['steps']]==expected
        assert props['custom.thresholdsStyle']['mode']=='line'
    assert dashboard()['refresh']=='10s' and dashboard()['style']=='dark'


def test_diagnostics_are_collapsed_and_retained_off_main_area():
    main=dashboard()['panels']
    diag=next(p for p in main if p['title']=='Diagnose / Entwicklung')
    assert diag['type']=='row' and diag['collapsed'] is True
    assert {p['id'] for p in diag['panels']}=={22,26,27,28}
    forbidden=('raw_mv_5m','ec_plateau_ref','ec_drop_from_plateau',
               'ec_min_since_plateau','ec_recovery_from_min','trend_1m','trend_3m',
               'trend_5m','rise_from_min_5m','trend_accel_3m','trend_accel_5m',
               'cusum_s','baseline_mu','baseline_sigma',"details->>'z'")
    primary_sql=' '.join(t['rawSql'] for p in main if p['type']!='row' for t in p.get('targets',[]))
    diagnostic_sql=' '.join(t['rawSql'] for p in diag['panels'] for t in p.get('targets',[]))
    for field in forbidden:
        assert field not in primary_sql and field in diagnostic_sql
    assert 'Vergleichsmarker' in {p['title'] for p in diag['panels']}
    assert 'raw_mv_1m' in primary_sql and 'raw_mv_1m' in diagnostic_sql
    ids=[p['id'] for p in all_panels()]
    assert len(ids)==len(set(ids))
    assert not any('transition_reason' in t.get('rawSql','') for p in all_panels() for t in p.get('targets',[]))
