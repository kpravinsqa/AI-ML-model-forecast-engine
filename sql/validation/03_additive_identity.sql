-- forecast = MAX(0, trend + seasonality + holiday_effect) within rounding tolerance (expect 0 rows)
SELECT run_id, product_id, location_id, week_start, trend, seasonality, holiday_effect, forecast
FROM forecast_output
WHERE ABS(forecast - MAX(0, trend + seasonality + holiday_effect)) > 0.001;
