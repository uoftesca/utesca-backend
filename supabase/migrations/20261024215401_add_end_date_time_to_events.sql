-- Add an optional end date and time to events in both application schemas.

ALTER TABLE test.events
ADD COLUMN end_date_time TIMESTAMPTZ NULL;

ALTER TABLE prod.events
ADD COLUMN end_date_time TIMESTAMPTZ NULL;

-- Rollback (run manually if needed):
-- ALTER TABLE test.events DROP COLUMN IF EXISTS end_date_time;
-- ALTER TABLE prod.events DROP COLUMN IF EXISTS end_date_time;
