"""Deterministic synthetic sales history (104 weeks) with trend, yearly seasonality and holiday spikes."""
from __future__ import annotations

import math
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HISTORY_END = date(2026, 9, 28)          # Monday
WEEKS = 104

PRODUCTS = [  # id, name, status, base, weekly trend, seasonal amplitude, holiday uplift
    ("SKU-TEA", "Masala Tea 500g", "ACTIVE", 400, 1.2, 60, 140),
    ("SKU-GHEE", "Cow Ghee 1L", "ACTIVE", 250, 0.6, 35, 190),
    ("SKU-RICE", "Basmati Rice 5kg", "ACTIVE", 600, 0.9, 25, 60),
    ("SKU-SWT", "Kaju Katli 250g", "ACTIVE", 90, 0.1, 15, 260),
    ("SKU-UMB", "Umbrella Large", "ACTIVE", 120, -0.6, 95, 0),       # strong monsoon seasonality
    ("SKU-DVD", "DVD Player", "ACTIVE", 150, -1.4, 10, 0),           # end-of-life ramp-down -> clipping at 0
    ("SKU-OLD", "Legacy Biscuit 100g", "DISCONTINUED", 80, -0.5, 5, 10),
    ("SKU-NEW", "Millet Muesli 400g", "ACTIVE", 70, 2.0, 5, 10),     # launched 6 weeks ago
]
LOCATIONS = [("PUN", "Pune DC", "West"), ("MUM", "Mumbai DC", "West"), ("BLR", "Bengaluru DC", "South")]
HOLIDAYS = {  # Monday of the holiday week
    date(2024, 11, 4): "Diwali", date(2025, 10, 20): "Diwali", date(2026, 11, 9): "Diwali",
    date(2024, 12, 23): "Christmas", date(2025, 12, 22): "Christmas", date(2026, 12, 21): "Christmas",
    date(2025, 3, 10): "Holi", date(2026, 3, 2): "Holi", date(2027, 3, 22): "Holi",
    date(2025, 8, 25): "Ganesh Chaturthi", date(2026, 9, 14): "Ganesh Chaturthi",
}


def season_week(d: date) -> int:
    return min(d.isocalendar()[1], 52)


def build(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript((ROOT / "sql" / "schema.sql").read_text())
    rnd = random.Random(7)
    con.executemany("INSERT INTO product VALUES (?,?,?)", [(p[0], p[1], p[2]) for p in PRODUCTS])
    con.executemany("INSERT INTO location VALUES (?,?,?)", LOCATIONS)
    con.executemany("INSERT INTO holiday_calendar VALUES (?,?)", [(d.isoformat(), n) for d, n in HOLIDAYS.items()])
    con.executemany("INSERT INTO engine_config VALUES (?,?)", [
        ("horizon_weeks", "26"), ("holdout_weeks", "8"), ("min_history_weeks", "26"),
        ("interval_z", "1.2816"), ("model_version", "gam-additive-2.3.1")])
    start = HISTORY_END - timedelta(weeks=WEEKS - 1)
    rows = []
    for pid, _, status, base, trend, amp, uplift in PRODUCTS:
        for li, (loc, *_rest) in enumerate(LOCATIONS):
            loc_factor = 1 + 0.15 * li
            for w in range(WEEKS):
                d = start + timedelta(weeks=w)
                if pid == "SKU-NEW" and w < WEEKS - 6:
                    continue
                if status == "DISCONTINUED" and w > WEEKS - 10:
                    continue
                phase = 2 * math.pi * (season_week(d) - 26) / 52     # peak around July (monsoon)
                value = (base + trend * w + amp * math.cos(phase) + (uplift if d in HOLIDAYS else 0)) * loc_factor
                rows.append((pid, loc, d.isoformat(), max(0, int(round(value + rnd.gauss(0, base * 0.04))))))
    con.executemany("INSERT INTO sales_history VALUES (?,?,?,?)", rows)
    con.commit()
    con.close()
    return path


if __name__ == "__main__":
    print("Seeded", build(ROOT / "db" / "forecast.db"))
