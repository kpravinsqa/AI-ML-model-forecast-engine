-- holiday_effect must be exactly 0 in non-holiday weeks (expect 0 rows)
SELECT f.run_id, f.product_id, f.location_id, f.week_start, f.holiday_effect
FROM forecast_output f LEFT JOIN holiday_calendar h ON h.week_start = f.week_start
WHERE h.week_start IS NULL AND f.holiday_effect <> 0;
