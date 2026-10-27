import pytest


@pytest.mark.model
def test_holiday_effect_applied_in_holiday_weeks(q, run_id):
    """Holiday-sensitive items must carry a positive uplift in forecast-horizon holiday weeks."""
    rows = q("""SELECT f.product_id, f.week_start, f.holiday_effect FROM forecast_output f
                JOIN holiday_calendar h ON h.week_start = f.week_start
                WHERE f.run_id = ? AND f.product_id IN ('SKU-SWT', 'SKU-GHEE', 'SKU-TEA')""", (run_id,))
    assert rows, "expected holiday weeks inside the horizon"
    assert all(r["holiday_effect"] > 0 for r in rows)


@pytest.mark.model
@pytest.mark.parametrize("week", ["2026-11-09", "2026-12-21", "2027-03-22"], ids=["Diwali", "Christmas", "Holi"])
def test_holiday_week_forecast_exceeds_neighbours(q, run_id, week):
    rows = q("""SELECT week_start, forecast FROM forecast_output WHERE run_id = ? AND product_id = 'SKU-SWT'
                AND location_id = 'PUN' AND week_start BETWEEN date(?, '-7 days') AND date(?, '+7 days')
                ORDER BY week_start""", (run_id, week, week))
    before, peak, after = (r["forecast"] for r in rows)
    assert peak > before * 1.5 and peak > after * 1.5


@pytest.mark.model
def test_negative_raw_forecasts_are_clipped_to_zero(q, run_id):
    clipped = q("""SELECT forecast, trend + seasonality + holiday_effect AS raw FROM forecast_output
                   WHERE run_id = ? AND trend + seasonality + holiday_effect < 0""", (run_id,))
    assert clipped, "ramp-down item should produce negative raw values"
    assert all(r["forecast"] == 0 for r in clipped)


@pytest.mark.model
def test_interval_widens_with_horizon(q, run_id):
    rows = q("""SELECT product_id, location_id, horizon_step, upper_80 - forecast AS half_width FROM forecast_output
                WHERE run_id = ? AND forecast > 0 ORDER BY 1, 2, 3""", (run_id,))
    by_series = {}
    for r in rows:
        by_series.setdefault((r["product_id"], r["location_id"]), []).append(r["half_width"])
    for series, widths in by_series.items():
        assert all(b >= a - 1e-4 for a, b in zip(widths, widths[1:])), f"{series} interval narrows"


@pytest.mark.model
def test_trend_direction_matches_history(q, run_id):
    """Growing items keep a rising trend; the ramp-down item keeps a falling one."""
    def slope(pid):
        first, last = q("""SELECT trend FROM forecast_output WHERE run_id = ? AND product_id = ? AND location_id = 'PUN'
                           AND horizon_step IN (1, 26) ORDER BY horizon_step""", (run_id, pid))
        return last["trend"] - first["trend"]
    assert slope("SKU-TEA") > 0
    assert slope("SKU-DVD") < 0


@pytest.mark.model
def test_monsoon_peak_in_umbrella_seasonality(q, run_id):
    peak_week = q.one("""SELECT season_week FROM seasonal_profile WHERE run_id = ? AND product_id = 'SKU-UMB'
                         AND location_id = 'MUM' ORDER BY seasonal_index DESC LIMIT 1""", (run_id,))
    assert 22 <= peak_week <= 32, f"peak at week {peak_week}, expected Jun-Aug"
