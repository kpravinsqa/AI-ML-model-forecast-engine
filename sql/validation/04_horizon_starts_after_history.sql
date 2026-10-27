-- First forecast week = history_end + 7 days and steps are weekly (expect 0 rows)
SELECT f.run_id, f.product_id, f.location_id, f.week_start, f.horizon_step, r.history_end
FROM forecast_output f JOIN engine_run r ON r.run_id = f.run_id
WHERE f.week_start <> date(r.history_end, '+' || (7 * f.horizon_step) || ' days');
