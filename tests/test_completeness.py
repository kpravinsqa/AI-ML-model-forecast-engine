import pytest

ELIGIBLE = """
    SELECT p.product_id, s.location_id FROM product p
    JOIN sales_history s ON s.product_id = p.product_id
    WHERE p.status = 'ACTIVE'
    GROUP BY 1, 2
    HAVING COUNT(*) >= (SELECT CAST(value AS INT) FROM engine_config WHERE param = 'min_history_weeks')
"""


@pytest.mark.completeness
@pytest.mark.smoke
def test_every_eligible_series_is_forecast(q, run_id):
    expected = {(r["product_id"], r["location_id"]) for r in q(ELIGIBLE)}
    actual = {(r["product_id"], r["location_id"]) for r in q(
        "SELECT DISTINCT product_id, location_id FROM forecast_output WHERE run_id = ?", (run_id,))}
    assert actual == expected


@pytest.mark.completeness
def test_each_series_has_full_horizon(q, run_id):
    horizon = q.one("SELECT horizon_weeks FROM engine_run WHERE run_id = ?", (run_id,))
    bad = q("""SELECT product_id, location_id, COUNT(*) n, MIN(horizon_step) lo, MAX(horizon_step) hi
               FROM forecast_output WHERE run_id = ? GROUP BY 1, 2
               HAVING n <> ? OR lo <> 1 OR hi <> ?""", (run_id, horizon, horizon))
    assert bad == []


@pytest.mark.completeness
def test_total_row_count(q, run_id):
    series = len(q(ELIGIBLE))
    assert q.one("SELECT COUNT(*) FROM forecast_output WHERE run_id = ?", (run_id,)) == series * 26


@pytest.mark.completeness
@pytest.mark.parametrize("product, reason", [("SKU-NEW", "INSUFFICIENT_HISTORY"), ("SKU-OLD", "DISCONTINUED")])
def test_skipped_series_are_logged(q, run_id, product, reason):
    rows = q("SELECT location_id, reason_code FROM engine_exception WHERE run_id = ? AND product_id = ? ORDER BY 1",
             (run_id, product))
    assert rows == [{"location_id": loc, "reason_code": reason} for loc in ("BLR", "MUM", "PUN")]
    assert q.one("SELECT COUNT(*) FROM forecast_output WHERE run_id = ? AND product_id = ?", (run_id, product)) == 0


@pytest.mark.completeness
def test_every_series_is_either_forecast_or_excepted(q, run_id):
    total = q.one("SELECT COUNT(*) FROM product CROSS JOIN location")
    forecast = q.one("SELECT COUNT(DISTINCT product_id || location_id) FROM forecast_output WHERE run_id = ?", (run_id,))
    excepted = q.one("SELECT COUNT(*) FROM engine_exception WHERE run_id = ?", (run_id,))
    assert forecast + excepted == total


@pytest.mark.completeness
def test_backtest_covers_holdout_window(q, run_id):
    bad = q("""SELECT b.product_id, b.location_id, COUNT(*) n, MIN(b.week_start) first, MAX(b.week_start) last
               FROM backtest_output b WHERE run_id = ? GROUP BY 1, 2
               HAVING n <> 8 OR last <> (SELECT MAX(week_start) FROM sales_history)""", (run_id,))
    assert bad == []
