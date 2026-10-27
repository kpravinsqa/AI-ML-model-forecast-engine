"""
Simplified additive (GAM-style) weekly forecast engine.

    y(t) = trend(t) + seasonality(week_of_year) + holiday_effect(t) + noise

* trend        : OLS line over non-holiday weeks
* seasonality  : mean de-trended residual per week-of-year, circularly smoothed (±2 weeks), centred to sum 0
* holiday      : mean residual uplift in holiday weeks, applied only to holiday weeks
* forecast     : max(0, trend + seasonality + holiday)
* 80 % interval: forecast ± z·σ·√(1 + h/52), lower bound floored at 0

It exists so the *database outputs* of a forecast engine can be tested; it is not a
production model and contains no proprietary algorithm.
"""
from __future__ import annotations

import math
import os
import sqlite3
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

DEFECTS = os.getenv("INJECT_DEFECTS") == "1"


def season_week(d: date) -> int:
    return min(d.isocalendar()[1], 52)


class SeriesModel:
    def __init__(self, history: list[tuple[date, int]], holidays: set[date]):
        self.start = history[0][0]
        self.holidays = holidays
        pts = [(self._x(d), y, d) for d, y in history]
        base = [(x, y) for x, y, d in pts if d not in holidays] or [(x, y) for x, y, _ in pts]
        n = len(base)
        mx = sum(x for x, _ in base) / n
        my = sum(y for _, y in base) / n
        sxx = sum((x - mx) ** 2 for x, _ in base) or 1
        self.slope = sum((x - mx) * (y - my) for x, y in base) / sxx
        self.intercept = my - self.slope * mx

        buckets: dict[int, list[float]] = {w: [] for w in range(1, 53)}
        for x, y, d in pts:
            if d not in holidays:
                buckets[season_week(d)].append(y - self.trend(x))
        raw = {w: (sum(v) / len(v) if v else 0.0) for w, v in buckets.items()}
        smooth = {w: sum(raw[(w - 1 + k) % 52 + 1] for k in range(-2, 3)) / 5 for w in range(1, 53)}
        mean = sum(smooth.values()) / 52
        self.season = {w: v - (0 if DEFECTS else mean) for w, v in smooth.items()}        # D3

        hol = [y - self.trend(x) - self.season[season_week(d)] for x, y, d in pts if d in holidays]
        self.holiday_uplift = sum(hol) / len(hol) if hol else 0.0
        resid = [y - self.components(d)[3] for _, y, d in pts]
        self.sigma = statistics.pstdev(resid) if len(resid) > 1 else 0.0

    def _x(self, d: date) -> int:
        return (d - self.start).days // 7

    def trend(self, x: float) -> float:
        return self.intercept + self.slope * x

    def components(self, d: date):
        t = self.trend(self._x(d))
        s = self.season[season_week(d)]
        h = self.holiday_uplift if d in self.holidays else 0.0
        return t, s, h, t + s + h


def _r(v: float) -> float:
    return round(v, 4)


def _backtest(con, run_id, pid, loc, hist, holdout, holidays):
    bt_model = SeriesModel(hist[:-holdout], holidays)
    actual_sum = abs_err = signed_err = 0.0
    apes = []
    for d, actual in hist[-holdout:]:
        pred = _r(max(0.0, bt_model.components(d)[3]))
        con.execute("INSERT INTO backtest_output VALUES (?,?,?,?,?,?)", (run_id, pid, loc, d.isoformat(), actual, pred))
        actual_sum += actual
        abs_err += abs(actual - pred)
        signed_err += pred - actual
        if actual > 0:
            apes.append(abs(actual - pred) / actual)
    mape = _r(100 * sum(apes) / len(apes)) if apes else 0.0
    wape = mape if DEFECTS else _r(100 * abs_err / actual_sum)                       # D5
    con.execute("INSERT INTO forecast_accuracy VALUES (?,?,?,?,?,?,?)",
                (run_id, pid, loc, holdout, mape, wape, _r(100 * signed_err / actual_sum)))


def run(db_path: Path, **config_overrides) -> int:
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON")
    cfg = dict(con.execute("SELECT param, value FROM engine_config").fetchall())
    cfg.update({k: str(v) for k, v in config_overrides.items()})
    horizon, holdout = int(cfg["horizon_weeks"]), int(cfg["holdout_weeks"])
    min_hist, z = int(cfg["min_history_weeks"]), float(cfg["interval_z"])
    holidays = {date.fromisoformat(r[0]) for r in con.execute("SELECT week_start FROM holiday_calendar")}
    history_end = date.fromisoformat(con.execute("SELECT MAX(week_start) FROM sales_history").fetchone()[0])

    run_id = con.execute(
        "INSERT INTO engine_run(started_at, status, model_version, history_end, horizon_weeks) VALUES (?,?,?,?,?)",
        (datetime.now().isoformat(timespec="microseconds"), "RUNNING", cfg["model_version"], history_end.isoformat(), horizon),
    ).lastrowid

    series = con.execute("""SELECT p.product_id, l.location_id, p.status FROM product p CROSS JOIN location l
                            ORDER BY 1, 2""").fetchall()
    for pid, loc, status in series:
        hist = [(date.fromisoformat(d), u) for d, u in con.execute(
            "SELECT week_start, units FROM sales_history WHERE product_id=? AND location_id=? ORDER BY week_start", (pid, loc))]
        if status == "DISCONTINUED" and not DEFECTS:                                     # D2
            con.execute("INSERT INTO engine_exception VALUES (?,?,?,?,?)", (run_id, pid, loc, "DISCONTINUED", None))
            continue
        if len(hist) < min_hist:
            con.execute("INSERT INTO engine_exception VALUES (?,?,?,?,?)",
                        (run_id, pid, loc, "INSUFFICIENT_HISTORY", f"{len(hist)} weeks < {min_hist}"))
            continue

        # ---- hold-out back-test (needs at least 4 training weeks) ------------
        if len(hist) - holdout < 4:
            con.execute("INSERT INTO engine_exception VALUES (?,?,?,?,?)",
                        (run_id, pid, loc, "BACKTEST_SKIPPED", f"{len(hist)} weeks <= holdout {holdout} + 4"))
        else:
            _backtest(con, run_id, pid, loc, hist, holdout, holidays)

        # ---- production forecast ------------------------------------------
        model = SeriesModel(hist, holidays)
        for w in range(1, 53):
            con.execute("INSERT INTO seasonal_profile VALUES (?,?,?,?,?)", (run_id, pid, loc, w, _r(model.season[w])))
        first = history_end if DEFECTS else history_end + timedelta(weeks=1)               # D1
        for step in range(1, horizon + 1):
            d = first + timedelta(weeks=step - 1)
            t, s, h, raw = model.components(d)
            t, s, h = _r(t), _r(s), _r(h)
            fc = _r(t + s + h) if DEFECTS else _r(max(0.0, t + s + h))                     # D4
            width = z * model.sigma * math.sqrt(1 + step / 52)
            con.execute("INSERT INTO forecast_output VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (run_id, pid, loc, d.isoformat(), step, t, s, h, fc, _r(max(0.0, fc - width)), _r(fc + width)))

    con.execute("UPDATE engine_run SET status='SUCCESS', finished_at=? WHERE run_id=?",
                (datetime.now().isoformat(timespec="microseconds"), run_id))
    con.commit()
    con.close()
    return run_id


if __name__ == "__main__":
    from engine.seed import build

    root = Path(__file__).resolve().parent.parent
    db = build(root / "db" / "forecast.db")
    print("Run", run(db), "written to", db)
