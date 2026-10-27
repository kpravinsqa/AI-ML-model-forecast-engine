-- Discontinued products must not be forecast (expect 0 rows)
SELECT f.run_id, f.product_id, COUNT(*) AS n
FROM forecast_output f JOIN product p ON p.product_id = f.product_id
WHERE p.status = 'DISCONTINUED' GROUP BY 1, 2;
