-- 0 <= lower_80 <= forecast <= upper_80 (expect 0 rows)
SELECT run_id, product_id, location_id, week_start, lower_80, forecast, upper_80
FROM forecast_output
WHERE lower_80 < 0 OR lower_80 > forecast + 0.0001 OR upper_80 < forecast - 0.0001;
