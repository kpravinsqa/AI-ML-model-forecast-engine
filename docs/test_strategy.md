# Forecast Engine — Database Test Strategy

The engine writes its results to relational tables that planning screens, replenishment and reporting consume. These
tests treat the engine as a black box and validate **what lands in the database** after each run.

| Layer | Example checks |
|---|---|
| Run metadata | run status lifecycle, `finished_at > started_at`, model version format, `history_end = MAX(sales week)`, horizon recorded from config, every output row tied to a run |
| Completeness | every eligible series (ACTIVE and ≥ min history) is forecast; full horizon 1…H with no gaps; skipped series logged with a reason; forecast + exceptions = all series; back-test covers the last 8 weeks |
| Value integrity | no NULL / negative forecasts; `0 ≤ lower ≤ forecast ≤ upper`; first week = history_end + 7; discontinued items absent |
| Model properties | additive identity `forecast = max(0, trend + seasonality + holiday)`; seasonal index centred (Σ ≈ 0 over 52 weeks); holiday effect only in holiday weeks; holiday spike > 1.5× neighbours; clipping of negative raw values; interval widens with horizon; trend direction; monsoon seasonality peak |
| Accuracy | MAPE / WAPE / bias recomputed in SQL from back-test rows and compared with stored KPIs; stable items WAPE ≤ 15 % and \|bias\| ≤ 10 %; poor-accuracy items surfaced for review |
| Aggregation | location view = Σ product rows; national = Σ locations; relative location volumes preserved |
| Regression | deterministic re-run (SHA-256 of outputs); horizon 1 / 13 / 52 honoured; min-history threshold honoured, with a logged back-test skip instead of a crash |

## Seeded-defect proof

`INJECT_DEFECTS=1 pytest` runs the engine with five realistic bugs. The suite fails 13 checks, and every defect is caught:

| # | Seeded defect | Caught by |
|---|---|---|
| D1 | Horizon off by one (starts on last history week) | `04_horizon_starts_after_history`, back-test window |
| D2 | Discontinued items still forecast | `05_no_forecast_for_discontinued`, completeness |
| D3 | Seasonality not centred | `07_seasonality_not_centred` |
| D4 | Negative forecasts not clipped | `01_negative_or_null_forecast`, `03_additive_identity`, clipping test |
| D5 | WAPE stored with the MAPE formula | `08_wape_recalculation` |

## Real defect found while building the suite

Lowering `min_history_weeks` below the hold-out length crashed the run (`IndexError` in the back-test). The engine now
logs `BACKTEST_SKIPPED` and still forecasts the series; `test_min_history_threshold_config` guards it.
