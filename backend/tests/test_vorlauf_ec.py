from dataclasses import replace
import pytest
from disti.process_analysis import AnalysisConfig,ProcessAnalyzer,ProcessState as S
from test_process_analysis import ControlledTemperatureFeatures,slope_point,p


def analyzer(strong=True,baseline=True,temperature=82):
    a=ProcessAnalyzer();a.process_state=S.AUFHEIZEN
    f=ControlledTemperatureFeatures();a.features=f
    if baseline:
        for i in range(-15,0): slope_point(a,f,i,2 if strong else .5,t=temperature)
    return a,f


def ec(a,f,i,value,slope=.5,**kw):
    f.value=replace(f.value,raw_mv_1m=value)
    return slope_point(a,f,i,slope,**kw)


def test_no_rise_and_thermal_peaks_or_collapse_never_start_vorlauf():
    a,f=analyzer()
    for i,s in enumerate([3,2,.1,0]*5):
        assert ec(a,f,i,100,s).process_state==S.AUFHEIZEN


def test_rise_requires_heating_evidence_in_current_phase():
    a,f=analyzer(strong=False)
    for i in range(6): assert ec(a,f,i,104).process_state==S.AUFHEIZEN
    assert not a.strong_heating_seen
    assert ec(a,f,6,108,1).process_state==S.AUFHEIZEN
    assert ec(a,f,7,108).process_state==S.AUFHEIZEN
    assert ec(a,f,8,108).process_state==S.VORLAUF


def test_complete_prior_window_excludes_current_value_and_inclusive_threshold():
    a,f=analyzer(baseline=False)
    for i in range(15): assert ec(a,f,i,100,2).process_state==S.AUFHEIZEN
    assert a.ec_baseline_5m is None
    assert ec(a,f,15,102).process_state==S.AUFHEIZEN
    assert a.ec_baseline_5m==100 and a.ec_rise_from_baseline==2
    assert ec(a,f,16,102).process_state==S.AUFHEIZEN
    assert ec(a,f,17,102).process_state==S.VORLAUF
    assert a.ec_start_since==p(15).time


def test_current_value_does_not_enter_prior_median():
    a,f=analyzer()
    a.config=replace(a.config,vorlauf_ec_baseline_window_seconds=20)
    ec(a,f,0,104)
    assert a.ec_baseline_5m==100
    ec(a,f,1,104)
    assert a.ec_baseline_5m==104 and a.ec_start_since is None


def test_previously_seen_heating_suffices_when_current_gradient_is_missing():
    a,f=analyzer()
    ec(a,f,0,104)
    ec(a,f,1,104)
    assert ec(a,f,2,104,slope=None).process_state==S.VORLAUF


def test_detector_start_preserves_contact_window_and_heating_evidence():
    a,f=analyzer(temperature=30)
    ec(a,f,0,104,t=30)
    ec(a,f,1,104,t=30)
    # The legacy detector starts here and resets its own heads/features state.
    assert ec(a,f,2,104,slope=None,t=76).process_state==S.VORLAUF
    assert a.ec_baseline_5m==100 and a.strong_heating_seen


def test_below_threshold_and_brief_rise_reset_persistence():
    a,f=analyzer()
    for i in range(4): assert ec(a,f,i,101.99).process_state==S.AUFHEIZEN
    for i in (4,5): assert ec(a,f,i,104).process_state==S.AUFHEIZEN
    assert ec(a,f,6,100).process_state==S.AUFHEIZEN
    assert a.ec_start_since is None
    for i in (7,8): assert ec(a,f,i,104).process_state==S.AUFHEIZEN
    assert ec(a,f,9,104).process_state==S.VORLAUF


@pytest.mark.parametrize('kind',['gap','missing','invalid','ec_outlier','pt_disconnect'])
def test_quality_breaks_baseline_and_persistence(kind):
    a,f=analyzer()
    ec(a,f,0,104);ec(a,f,1,104)
    kwargs={'mv':None} if kind=='missing' else {'invalid':True} if kind=='invalid' else {'mv':301} if kind=='ec_outlier' else {'pt':3300} if kind=='pt_disconnect' else {}
    index=3 if kind=='gap' else 2
    r=ec(a,f,index,104,**kwargs)
    assert r.process_state in (S.DATENLUECKE,S.SENSOR_UNGUELTIG)
    assert not a.ec_start_history and a.ec_start_since is None
    for i in range(index+1,index+16):
        assert ec(a,f,i,104).process_state==S.AUFHEIZEN
        assert a.ec_baseline_5m is None
    assert ec(a,f,index+16,104).process_state==S.AUFHEIZEN
    assert a.ec_baseline_5m==104


@pytest.mark.parametrize('temperature,pt',[(30,550),(60,700),(82,900)])
def test_no_absolute_temperature_or_pt_cooling_condition_and_no_regression(temperature,pt):
    a,f=analyzer(temperature=temperature)
    for i in range(2): assert ec(a,f,i,104,t=temperature,pt=pt+i).process_state==S.AUFHEIZEN
    assert ec(a,f,2,104,t=temperature,pt=pt+2).process_state==S.VORLAUF
    assert ec(a,f,3,100,3,t=82,pt=pt+3).process_state==S.VORLAUF


def test_next_process_discards_previous_strong_heating_and_persistence():
    a,f=analyzer();assert a.strong_heating_seen
    a.process_state=S.BEREIT
    for i in range(4):ec(a,f,i,100,.3)
    assert a.process_state==S.AUFHEIZEN and not a.strong_heating_seen
    for i in range(4,8):assert ec(a,f,i,104,.3).process_state==S.AUFHEIZEN
    a.reset();assert not a.ec_start_history and not a.strong_heating_seen


def test_ec_baseline_can_warm_up_while_ready_without_triggering():
    a=ProcessAnalyzer();f=ControlledTemperatureFeatures();a.features=f
    for i in range(18): assert ec(a,f,i,100,0).process_state==S.BEREIT
    assert a.ec_baseline_5m==100 and not a.strong_heating_seen


@pytest.mark.parametrize('kwargs',[{'vorlauf_ec_baseline_window_seconds':0},
    {'vorlauf_ec_baseline_window_seconds':301},{'vorlauf_ec_rise_threshold_mv':0},
    {'vorlauf_ec_rise_persistence_seconds':-1}])
def test_invalid_ec_configuration(kwargs):
    with pytest.raises(ValueError): AnalysisConfig(**kwargs)
