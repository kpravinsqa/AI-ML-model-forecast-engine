# Forecast Engine (GAM) — Database Testing

![Tests](https://github.com/kpravinsqa/db-testing-gam-forecast-engine/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![SQL](https://img.shields.io/badge/SQL-SQLite%20%7C%20ANSI-003B57) ![Domain](https://img.shields.io/badge/domain-Demand%20Forecasting-6a1b9a)

Database-level test framework for a **GAM-style (additive) weekly demand forecast engine**, based on the output
validation I did for the **GAM Forecast Engine** in the supply chain planning domain. Each engine run writes forecasts,
components, prediction intervals, seasonal profiles, back-tests and accuracy KPIs to SQL tables, and this suite checks
that everything landing there is complete, consistent and mathematically correct.

> **Confidentiality note:** the engine here is a small **textbook additive model** written for this portfolio
> (trend + seasonality + holiday). It contains no proprietary algorithm, client data or code.

## Highlights

* **51 automated checks** across 7 layers: metadata, completeness, value integrity, model properties, accuracy, aggregation, regression
* **Model-aware assertions**: additive identity, centred seasonality, holiday-only effects, interval ordering and widening, clipping at zero
* **KPI verification in SQL**: MAPE, WAPE and bias recomputed from back-test rows and compared to the stored values
* **Business thresholds**: stable items WAPE ≤ 15 % and |bias| ≤ 10 %; volatile items (monsoon umbrella, end-of-life DVD) surfaced for review
* **Determinism and config tests**: SHA-256 output digest across re-runs; horizon 1 / 13 / 52; min-history threshold
* **Seeded-defect proof**: `INJECT_DEFECTS=1` plants 5 engine bugs, and the suite catches all of them (CI asserts this)
* **Found a real bug**: a short-history crash in the back-test, now fixed and guarded ([details](docs/test_strategy.md))
* **Excel QA workbook**: run summary, validation checks, accuracy league table, exceptions, location totals

## Quick start

```bash
git clone https://github.com/kpravinsqa/db-testing-gam-forecast-engine.git
cd db-testing-gam-forecast-engine
pip install -r requirements.txt

pytest                                    # full suite + reports/report.html
pytest -m accuracy                        # one layer
INJECT_DEFECTS=1 pytest                   # watch seeded defects get caught
python -m reports_tool.forecast_qa_report # reports/forecast_qa_report.xlsx
python -m engine.gam_engine               # build db/forecast.db to explore in DBeaver / DB Browser
```

## Data model

`product`, `location`, `sales_history` (104 weeks), `holiday_calendar` (Diwali, Christmas, Holi, Ganesh Chaturthi),
`engine_config`, `engine_run`, `forecast_output`, `seasonal_profile`, `backtest_output`, `forecast_accuracy`,
`engine_exception`, view `v_forecast_by_location`. See [sql/schema.sql](sql/schema.sql).

## Structure

```
engine/seed.py               synthetic history: trend, yearly seasonality, holiday spikes, new + discontinued items
engine/gam_engine.py         additive engine (+ INJECT_DEFECTS switch)
sql/validation/*.sql         9 zero-row validation queries (usable in any SQL client)
tests/                       metadata · completeness · model properties · accuracy · aggregation & regression
reports_tool/                Excel QA workbook
docs/test_strategy.md        layers, seeded defects, real defect found
```

## Author

**Pravin Khedkar**, QA Lead / SDET · [@kpravinsqa](https://github.com/kpravinsqa)
