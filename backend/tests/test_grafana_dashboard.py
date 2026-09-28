import json
from pathlib import Path


DASHBOARD_PATH = Path(__file__).parents[2] / "grafana" / "dashboards" / "Distillation.json"


def _dashboard():
    return json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))


def test_experimental_analysis_row_is_expanded_and_has_expected_panels():
    panels = _dashboard()["panels"]
    row_index = next(i for i, panel in enumerate(panels) if panel["title"] == "Analyse / Experimental")
    row = panels[row_index]

    assert row["type"] == "row"
    assert row["collapsed"] is False
    assert [panel["title"] for panel in panels[row_index + 1 : row_index + 6]] == [
        "Kesseldampf – Dynamik",
        "EC – Dynamik",
        "Prozessanalyse",
        "Temperaturdifferenz",
        "Kühler – Verlauf",
    ]


def test_analysis_queries_are_fixed_window_read_only_and_index_constrained():
    analysis_titles = {
        "Kesseldampf – Dynamik",
        "EC – Dynamik",
        "Prozessanalyse",
        "Temperaturdifferenz",
        "Kühler – Verlauf",
    }

    for panel in _dashboard()["panels"]:
        if panel["title"] not in analysis_titles:
            continue
        sql = panel["targets"][0]["rawSql"]
        assert "sensor_measurements" in sql
        assert "$__timeFilter(time)" in sql
        assert "sensor_id" in sql
        assert "INTERVAL '1 minute'" in sql
        assert "$__interval" not in sql
        assert not any(statement in sql.upper() for statement in ("INSERT ", "UPDATE ", "DELETE "))


def test_derivatives_require_adjacent_minutes_and_guard_division():
    panels = {panel["title"]: panel for panel in _dashboard()["panels"]}
    for title in ("Kesseldampf – Dynamik", "EC – Dynamik"):
        sql = panels[title]["targets"][0]["rawSql"]
        assert "lag(smoothed_value) OVER (ORDER BY time)" in sql
        assert "elapsed_seconds = 60" in sql
        assert "* 60.0 / NULLIF(elapsed_seconds, 0)" in sql


def test_mixed_unit_panels_use_explicit_right_axis_overrides():
    panels = {panel["title"]: panel for panel in _dashboard()["panels"]}
    expected_right_axis_series = {
        "Kesseldampf – Dynamik": "dT/dt (°C/min)",
        "EC – Dynamik": "dEC/dt (µS/cm/min)",
        "Prozessanalyse": "EC (60-s-Mittel)",
    }
    for title, series in expected_right_axis_series.items():
        override = next(
            item for item in panels[title]["fieldConfig"]["overrides"]
            if item["matcher"]["options"] == series
        )
        properties = {item["id"]: item["value"] for item in override["properties"]}
        assert properties["custom.axisPlacement"] == "right"
