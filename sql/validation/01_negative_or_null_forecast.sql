-- Forecasts must be non-negative and not null (expect 0 rows)
SELECT run_id, product_id, location_id, week_start, forecast
FROM forecast_output WHERE forecast IS NULL OR forecast < 0;
