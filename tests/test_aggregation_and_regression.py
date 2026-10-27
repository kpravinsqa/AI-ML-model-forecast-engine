import hashlib
import sqlite3

import pytest

from engine.gam_engine import run


def output_digest(path, run_id):
    con = sqlite3.connect(path)
    h = hashlib.sha256()
    for row in con.execute("""SELECT product_id, location_id, week_start, trend, seasonality, holiday_effect,
                                     forecast, lower_80, upper_80 FROM forecast_output WHERE run_id = ?
                              ORDER BY 1, 2, 3""", (run_id,)):
        h.update(repr(row).encode())
    con.close()
    return h.hexdigest()


@pytest.mark.aggregation
def test_national_total_equals_sum_of_locations(q, run_id):
    national = q.one("SELECT ROUND(SUM(forecast), 2) FROM forecast_output WHERE run_id = ?", (run_id,))
    by_loc = q.one("SELECT ROUND(SUM(total_forecast), 2) FROM v_forecast_by_location WHERE run_id = ?", (run_id,))
    assert national == by_loc


@pytest.mark.aggregation
def test_location_scaling_is_preserved(q, run_id):
    """History was generated with BLR > MUM > PUN volume; the forecast must keep that ordering."""
    totals = {r["location_id"]: r["t"] for r in q(
        "SELECT location_id, SUM(forecast) t FROM forecast_output WHERE run_id = ? AND product_id = 'SKU-RICE' GROUP BY 1",
        (run_id,))}
    assert totals["BLR"] > totals["MUM"] > totals["PUN"]


@pytest.mark.regression
def test_engine_is_deterministic(fresh_db):
    first = run(fresh_db)
    second = run(fresh_db)
    assert output_digest(fresh_db, first) == output_digest(fresh_db, second)


@pytest.mark.regression
@pytest.mark.parametrize("horizon", [1, 13, 52])
def test_horizon_config_respected(fresh_db, horizon):
    rid = run(fresh_db, horizon_weeks=horizon)
    con = sqlite3.connect(fresh_db)
    counts = {r[0] for r in con.execute(
        "SELECT COUNT(*) FROM forecast_output WHERE run_id = ? GROUP BY product_id, location_id", (rid,))}
    con.close()
    assert counts == {horizon}


@pytest.mark.regression
def test_min_history_threshold_config(fresh_db):
    rid = run(fresh_db, min_history_weeks=5)          # SKU-NEW has 6 weeks -> now eligible
    con = sqlite3.connect(fresh_db)
    n = con.execute("SELECT COUNT(*) FROM forecast_output WHERE run_id = ? AND product_id = 'SKU-NEW'", (rid,)).fetchone()[0]
    skipped = con.execute("""SELECT COUNT(*) FROM engine_exception WHERE run_id = ? AND product_id = 'SKU-NEW'
                             AND reason_code = 'BACKTEST_SKIPPED'""", (rid,)).fetchone()[0]
    con.close()
    assert n == 3 * 26
    assert skipped == 3, "too little history for a hold-out back-test must be logged, not crash the run"
