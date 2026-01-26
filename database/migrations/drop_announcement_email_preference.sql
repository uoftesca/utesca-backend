-- Migration: Drop old announcement_email_preference column
-- Date: January 3, 2026 (Run 7+ days after add_notification_preferences.sql)
-- Description: Removes legacy announcement_email_preference column after verification
-- IMPORTANT: Only run after confirming notification_preferences works in production

-- ============================================================================
-- PRE-MIGRATION VERIFICATION
-- ============================================================================

-- Verify notification_preferences column exists and has data
-- SELECT COUNT(*) FROM test.users WHERE notification_preferences IS NOT NULL;
-- SELECT COUNT(*) FROM prod.users WHERE notification_preferences IS NOT NULL;

-- Verify all expected keys are present
-- SELECT COUNT(*) FROM test.users WHERE
--   notification_preferences ? 'announcements' AND
--   notification_preferences ? 'rsvp_changes' AND
--   notification_preferences ? 'new_application_submitted';

-- ============================================================================
-- OPTIONAL: BACKUP OLD VALUES
-- ============================================================================

-- Create backup table with old values (optional, for safety)
-- CREATE TABLE test.users_announcement_preference_backup AS
-- SELECT id, announcement_email_preference FROM test.users;

-- CREATE TABLE prod.users_announcement_preference_backup AS
-- SELECT id, announcement_email_preference FROM prod.users;

-- ============================================================================
-- DROP OLD COLUMN
-- ============================================================================

-- Drop old column from test schema
ALTER TABLE test.users
DROP COLUMN announcement_email_preference;

-- Drop old column from prod schema
ALTER TABLE prod.users
DROP COLUMN announcement_email_preference;

-- ============================================================================
-- POST-MIGRATION VERIFICATION
-- ============================================================================

-- Verify column is dropped
-- SELECT column_name FROM information_schema.columns
-- WHERE table_schema = 'test' AND table_name = 'users';

-- Verify application still works
-- Test user profile updates
-- Test notification filtering queries

-- ============================================================================
-- ROLLBACK SCRIPT (if you need to restore old column)
-- ============================================================================

-- WARNING: This rollback assumes you created backup tables above

-- ALTER TABLE test.users ADD COLUMN announcement_email_preference VARCHAR;
-- UPDATE test.users u
-- SET announcement_email_preference = b.announcement_email_preference
-- FROM test.users_announcement_preference_backup b
-- WHERE u.id = b.id;

-- ALTER TABLE prod.users ADD COLUMN announcement_email_preference VARCHAR;
-- UPDATE prod.users u
-- SET announcement_email_preference = b.announcement_email_preference
-- FROM prod.users_announcement_preference_backup b
-- WHERE u.id = b.id;
