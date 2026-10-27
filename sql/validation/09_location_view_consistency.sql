-- v_forecast_by_location equals the sum of product-level rows (expect 0 rows)
SELECT v.run_id, v.location_id, v.week_start, v.total_forecast, s.calc
FROM v_forecast_by_location v
JOIN (SELECT run_id, location_id, week_start, SUM(forecast) AS calc FROM forecast_output GROUP BY 1, 2, 3) s
  USING (run_id, location_id, week_start)
WHERE ABS(v.total_forecast - s.calc) > 0.001;
