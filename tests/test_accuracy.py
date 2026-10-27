import pytest

STABLE_ITEMS = ("SKU-TEA", "SKU-GHEE", "SKU-RICE", "SKU-SWT")
WAPE_THRESHOLD = 15.0          # % - business acceptance for stable items
BIAS_THRESHOLD = 10.0          # % - absolute


@pytest.mark.accuracy
def test_mape_recomputed_from_backtest(q, run_id):
    rows = q("""SELECT a.product_id, a.location_id, a.mape,
                       ROUND(100.0 * AVG(ABS(b.actual - b.predicted) * 1.0 / b.actual), 4) AS calc
                FROM forecast_accuracy a JOIN backtest_output b USING (run_id, product_id, location_id)
                WHERE a.run_id = ? AND b.actual > 0 GROUP BY 1, 2, 3""", (run_id,))
    assert rows
    assert all(abs(r["mape"] - r["calc"]) < 0.001 for r in rows)


@pytest.mark.accuracy
@pytest.mark.smoke
@pytest.mark.parametrize("product", STABLE_ITEMS)
def test_stable_items_meet_wape_target(q, run_id, product):
    worst = q.one("SELECT MAX(wape) FROM forecast_accuracy WHERE run_id = ? AND product_id = ?", (run_id, product))
    assert worst <= WAPE_THRESHOLD, f"{product} WAPE {worst}% > {WAPE_THRESHOLD}%"


@pytest.mark.accuracy
@pytest.mark.parametrize("product", STABLE_ITEMS)
def test_stable_items_bias_within_limit(q, run_id, product):
    worst = q.one("SELECT MAX(ABS(bias)) FROM forecast_accuracy WHERE run_id = ? AND product_id = ?", (run_id, product))
    assert worst <= BIAS_THRESHOLD


@pytest.mark.accuracy
def test_poor_accuracy_items_are_identified(q, run_id):
    """The exception report must surface the items planners need to review."""
    flagged = {r["product_id"] for r in q(
        "SELECT DISTINCT product_id FROM forecast_accuracy WHERE run_id = ? AND wape > ?", (run_id, WAPE_THRESHOLD))}
    assert flagged == {"SKU-UMB", "SKU-DVD"}


@pytest.mark.accuracy
def test_accuracy_row_per_forecast_series(q, run_id):
    assert q.one("SELECT COUNT(*) FROM forecast_accuracy WHERE run_id = ?", (run_id,)) == \
        q.one("SELECT COUNT(DISTINCT product_id || location_id) FROM forecast_output WHERE run_id = ?", (run_id,))
