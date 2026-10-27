-- =====================================================================
-- Forecast engine data model (synthetic re-creation for a portfolio)
-- =====================================================================
PRAGMA foreign_keys = ON;

CREATE TABLE product (
    product_id    TEXT PRIMARY KEY,
    product_name  TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('ACTIVE','DISCONTINUED'))
);

CREATE TABLE location (
    location_id   TEXT PRIMARY KEY,
    location_name TEXT NOT NULL,
    region        TEXT NOT NULL
);

CREATE TABLE sales_history (
    product_id    TEXT NOT NULL REFERENCES product(product_id),
    location_id   TEXT NOT NULL REFERENCES location(location_id),
    week_start    DATE NOT NULL,             -- Monday
    units         INTEGER NOT NULL CHECK (units >= 0),
    PRIMARY KEY (product_id, location_id, week_start)
);

CREATE TABLE holiday_calendar (
    week_start    DATE PRIMARY KEY,
    holiday_name  TEXT NOT NULL
);

CREATE TABLE engine_config (
    param         TEXT PRIMARY KEY,
    value         TEXT NOT NULL
);

CREATE TABLE engine_run (
    run_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    status        TEXT NOT NULL CHECK (status IN ('RUNNING','SUCCESS','FAILED')),
    model_version TEXT NOT NULL,
    history_end   DATE NOT NULL,
    horizon_weeks INTEGER NOT NULL
);

-- Additive model output: forecast = max(0, trend + seasonality + holiday_effect)
CREATE TABLE forecast_output (
    run_id         INTEGER NOT NULL REFERENCES engine_run(run_id),
    product_id     TEXT NOT NULL REFERENCES product(product_id),
    location_id    TEXT NOT NULL REFERENCES location(location_id),
    week_start     DATE NOT NULL,
    horizon_step   INTEGER NOT NULL,
    trend          REAL NOT NULL,
    seasonality    REAL NOT NULL,
    holiday_effect REAL NOT NULL,
    forecast       REAL NOT NULL,
    lower_80       REAL NOT NULL,
    upper_80       REAL NOT NULL,
    PRIMARY KEY (run_id, product_id, location_id, week_start)
);

CREATE TABLE seasonal_profile (
    run_id        INTEGER NOT NULL REFERENCES engine_run(run_id),
    product_id    TEXT NOT NULL,
    location_id   TEXT NOT NULL,
    season_week   INTEGER NOT NULL CHECK (season_week BETWEEN 1 AND 52),
    seasonal_index REAL NOT NULL,
    PRIMARY KEY (run_id, product_id, location_id, season_week)
);

-- Hold-out back-test used to compute accuracy KPIs
CREATE TABLE backtest_output (
    run_id        INTEGER NOT NULL REFERENCES engine_run(run_id),
    product_id    TEXT NOT NULL,
    location_id   TEXT NOT NULL,
    week_start    DATE NOT NULL,
    actual        INTEGER NOT NULL,
    predicted     REAL NOT NULL,
    PRIMARY KEY (run_id, product_id, location_id, week_start)
);

CREATE TABLE forecast_accuracy (
    run_id        INTEGER NOT NULL REFERENCES engine_run(run_id),
    product_id    TEXT NOT NULL,
    location_id   TEXT NOT NULL,
    holdout_weeks INTEGER NOT NULL,
    mape          REAL NOT NULL,
    wape          REAL NOT NULL,
    bias          REAL NOT NULL,
    PRIMARY KEY (run_id, product_id, location_id)
);

CREATE TABLE engine_exception (
    run_id        INTEGER NOT NULL REFERENCES engine_run(run_id),
    product_id    TEXT NOT NULL,
    location_id   TEXT NOT NULL,
    reason_code   TEXT NOT NULL,
    detail        TEXT
);

CREATE VIEW v_forecast_by_location AS
SELECT run_id, location_id, week_start, ROUND(SUM(forecast), 4) AS total_forecast
FROM forecast_output GROUP BY run_id, location_id, week_start;
