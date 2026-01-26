-- Migration: Add notification_preferences JSONB column to users table
-- Date: January 3, 2026
-- Description: Migrates from single announcement_email_preference field to granular JSONB notification system
-- Applies to: BOTH test.users and prod.users schemas

-- ============================================================================
-- PHASE 1: ADD JSONB COLUMN
-- ============================================================================

-- Add new JSONB column to test schema
ALTER TABLE test.users
ADD COLUMN notification_preferences JSONB;

-- Add new JSONB column to prod schema
ALTER TABLE prod.users
ADD COLUMN notification_preferences JSONB;

-- ============================================================================
-- PHASE 2: DATA MIGRATION
-- ============================================================================

-- Migrate existing data in test schema
UPDATE test.users
SET notification_preferences =
  CASE
    WHEN announcement_email_preference = 'all' THEN
      '{"announcements": "all", "rsvp_changes": true, "new_application_submitted": true}'::jsonb
    WHEN announcement_email_preference = 'urgent_only' THEN
      '{"announcements": "urgent_only", "rsvp_changes": false, "new_application_submitted": false}'::jsonb
    WHEN announcement_email_preference = 'none' THEN
      '{"announcements": "none", "rsvp_changes": false, "new_application_submitted": false}'::jsonb
    ELSE
      -- Default fallback for any unexpected values
      '{"announcements": "all", "rsvp_changes": true, "new_application_submitted": true}'::jsonb
  END;

-- Migrate existing data in prod schema
UPDATE prod.users
SET notification_preferences =
  CASE
    WHEN announcement_email_preference = 'all' THEN
      '{"announcements": "all", "rsvp_changes": true, "new_application_submitted": true}'::jsonb
    WHEN announcement_email_preference = 'urgent_only' THEN
      '{"announcements": "urgent_only", "rsvp_changes": false, "new_application_submitted": false}'::jsonb
    WHEN announcement_email_preference = 'none' THEN
      '{"announcements": "none", "rsvp_changes": false, "new_application_submitted": false}'::jsonb
    ELSE
      -- Default fallback for any unexpected values
      '{"announcements": "all", "rsvp_changes": true, "new_application_submitted": true}'::jsonb
  END;

-- ============================================================================
-- PHASE 3: ADD CONSTRAINTS
-- ============================================================================

-- Set NOT NULL constraint on test schema
ALTER TABLE test.users
ALTER COLUMN notification_preferences SET NOT NULL;

-- Set NOT NULL constraint on prod schema
ALTER TABLE prod.users
ALTER COLUMN notification_preferences SET NOT NULL;

-- Add CHECK constraint to ensure required keys exist (test schema)
ALTER TABLE test.users
ADD CONSTRAINT notification_preferences_valid
CHECK (
  notification_preferences ? 'announcements' AND
  notification_preferences ? 'rsvp_changes' AND
  notification_preferences ? 'new_application_submitted'
);

-- Add CHECK constraint to ensure required keys exist (prod schema)
ALTER TABLE prod.users
ADD CONSTRAINT notification_preferences_valid
CHECK (
  notification_preferences ? 'announcements' AND
  notification_preferences ? 'rsvp_changes' AND
  notification_preferences ? 'new_application_submitted'
);

-- ============================================================================
-- PHASE 4: ADD INDEXES FOR QUERY PERFORMANCE
-- ============================================================================

-- Add GIN index for efficient JSONB querying (test schema)
CREATE INDEX idx_notification_preferences_test
ON test.users USING GIN (notification_preferences);

-- Add GIN index for efficient JSONB querying (prod schema)
CREATE INDEX idx_notification_preferences_prod
ON prod.users USING GIN (notification_preferences);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify migration results (run manually after migration)
-- SELECT id, announcement_email_preference, notification_preferences FROM test.users LIMIT 10;
-- SELECT id, announcement_email_preference, notification_preferences FROM prod.users LIMIT 10;

-- Verify constraint is enforced (should fail)
-- INSERT INTO test.users (notification_preferences) VALUES ('{"announcements": "all"}'::jsonb);

-- ============================================================================
-- NOTES
-- ============================================================================

-- IMPORTANT:
-- 1. This migration keeps the old announcement_email_preference column intact
-- 2. Drop the old column only after 7 days of production verification
-- 3. See drop_announcement_email_preference.sql for Phase 2 migration
-- 4. Rollback script available below

-- ============================================================================
-- ROLLBACK SCRIPT (run only if migration fails)
-- ============================================================================

-- DROP INDEX IF EXISTS test.idx_notification_preferences_test;
-- DROP INDEX IF EXISTS prod.idx_notification_preferences_prod;
-- ALTER TABLE test.users DROP CONSTRAINT IF EXISTS notification_preferences_valid;
-- ALTER TABLE test.users DROP COLUMN IF EXISTS notification_preferences;
-- ALTER TABLE prod.users DROP CONSTRAINT IF EXISTS notification_preferences_valid;
-- ALTER TABLE prod.users DROP COLUMN IF EXISTS notification_preferences;
