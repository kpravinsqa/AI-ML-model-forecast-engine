-- Additive seasonal index must sum to ~0 over 52 weeks per series (expect 0 rows)
SELECT run_id, product_id, location_id, ROUND(SUM(seasonal_index), 4) AS season_sum, COUNT(*) AS weeks
FROM seasonal_profile GROUP BY 1, 2, 3
HAVING ABS(SUM(seasonal_index)) > 0.01 OR COUNT(*) <> 52;
