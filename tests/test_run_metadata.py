import re

import pytest


@pytest.mark.metadata
@pytest.mark.smoke
def test_latest_run_succeeded(q, run_id):
    run = q("SELECT * FROM engine_run WHERE run_id = ?", (run_id,))[0]
    assert run["status"] == "SUCCESS"
    assert run["finished_at"] > run["started_at"]


@pytest.mark.metadata
def test_model_version_semver(q, run_id):
    version = q.one("SELECT model_version FROM engine_run WHERE run_id = ?", (run_id,))
    assert re.fullmatch(r"gam-[a-z]+-\d+\.\d+\.\d+", version)


@pytest.mark.metadata
def test_history_end_matches_latest_sales_week(q, run_id):
    assert q.one("SELECT history_end FROM engine_run WHERE run_id = ?", (run_id,)) == \
        q.one("SELECT MAX(week_start) FROM sales_history")


@pytest.mark.metadata
def test_horizon_recorded_from_config(q, run_id):
    assert q.one("SELECT horizon_weeks FROM engine_run WHERE run_id = ?", (run_id,)) == \
        int(q.one("SELECT value FROM engine_config WHERE param = 'horizon_weeks'"))


@pytest.mark.metadata
@pytest.mark.parametrize("table", ["forecast_output", "seasonal_profile", "backtest_output", "forecast_accuracy", "engine_exception"])
def test_all_outputs_belong_to_a_run(q, table):
    assert q.one(f"SELECT COUNT(*) FROM {table} t LEFT JOIN engine_run r ON r.run_id = t.run_id WHERE r.run_id IS NULL") == 0
