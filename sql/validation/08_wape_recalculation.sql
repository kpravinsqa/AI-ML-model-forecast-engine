-- Stored WAPE / bias must equal values recomputed from the back-test rows (expect 0 rows)
SELECT a.run_id, a.product_id, a.location_id, a.wape, b.wape_calc, a.bias, b.bias_calc
FROM forecast_accuracy a
JOIN (SELECT run_id, product_id, location_id,
             ROUND(100.0 * SUM(ABS(actual - predicted)) / SUM(actual), 4) AS wape_calc,
             ROUND(100.0 * SUM(predicted - actual) / SUM(actual), 4)      AS bias_calc
      FROM backtest_output GROUP BY 1, 2, 3) b USING (run_id, product_id, location_id)
WHERE ABS(a.wape - b.wape_calc) > 0.001 OR ABS(a.bias - b.bias_calc) > 0.001;
